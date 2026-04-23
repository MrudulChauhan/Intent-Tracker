"""
Scan orchestrator for the intent-based DeFi OSINT tracker.

Coordinates all scanners, persists results via a Writer (SQLite in dev,
Supabase in production), deduplicates mentions, and optionally runs on a
weekly schedule via APScheduler.
"""

import argparse
import json
import logging
import os
import time
from datetime import date, datetime, timedelta
from typing import Any, Dict

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

# Scanners
from scanners.blogs import BlogScanner
from scanners.coingecko import CoinGeckoScanner
from scanners.defillama import DefiLlamaScanner
from scanners.github_scanner import GitHubScanner
from scanners.google_news import GoogleNewsScanner
from scanners.reddit import RedditScanner
from scanners.rss import RSSScanner

# Config
from core.config import settings

if settings.dune_api_key:
    from scanners.dune import DuneScanner
else:
    DuneScanner = None

# Writer — routes to Supabase or SQLite based on env
from core.writer import Writer, get_writer

# Processing
from processing.enrichment import extract_funding_info  # noqa: F401 (used elsewhere)
from processing.narratives import generate_weekly_narratives


logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)

_GITHUB_METRIC_SCANNERS = {"github"}

_SCANNER_CLASSES = [
    DefiLlamaScanner,
    CoinGeckoScanner,
    RedditScanner,
    RSSScanner,
    GoogleNewsScanner,
    GitHubScanner,
    BlogScanner,
]

if DuneScanner is not None:
    _SCANNER_CLASSES.append(DuneScanner)


def _map_github_metric(raw: dict) -> dict:
    today = datetime.utcnow().strftime("%Y-%m-%d")
    return {
        "repo_url": f"https://github.com/{raw.get('project_name', '')}",
        "stars": raw.get("stars"),
        "forks": raw.get("forks"),
        "open_issues": raw.get("open_issues"),
        "contributors_count": raw.get("contributors_count"),
        "last_commit_at": raw.get("last_push"),
        "commits_30d": raw.get("recent_commits_30d"),
        "snapshot_date": today,
    }


def _map_protocol_metric(raw: dict) -> dict:
    today = datetime.utcnow().strftime("%Y-%m-%d")
    chains = raw.get("chains")
    return {
        "tvl_usd": raw.get("tvl"),
        "volume_24h": raw.get("volume_24h"),
        "chain": json.dumps(chains) if isinstance(chains, list) else raw.get("chain"),
        "snapshot_date": today,
        "source": raw.get("source", ""),
    }


def _map_mention(raw: dict) -> dict:
    return {
        "source": raw.get("source", ""),
        "title": raw.get("title", ""),
        "url": raw.get("url") or raw.get("link", ""),
        "author": raw.get("author", ""),
        "content_snippet": (
            raw.get("content_snippet") or raw.get("text") or raw.get("snippet", "")
        ),
        "sentiment_score": raw.get("sentiment_score"),
        "upvotes": raw.get("upvotes") or raw.get("score", 0),
        "published_at": raw.get("published_at") or raw.get("published", ""),
    }


def _link_mention_project(writer: Writer, mention: dict) -> int | None:
    """Find a project by matching protocol names against mention title+content."""
    title = (mention.get("title") or "").lower()
    content = (mention.get("content_snippet") or "").lower()
    combined = f"{title} {content}"
    if not combined.strip():
        return None
    # Simple approach: fetch recent project names (done via writer in the
    # SQLite case, skipped for Supabase to avoid a listing round-trip).
    # The scanner's enrichment step already handled the hard match; we just
    # try a direct name lookup if mention looks like "<name>:" style.
    first_word = title.split(":", 1)[0].strip()
    if len(first_word) >= 3:
        return writer.find_project_id_by_name(first_word.title())
    return None


def _process_scan_result(scanner, result, writer: Writer) -> Dict[str, int]:
    """Persist a ScanResult via the Writer, returning per-entity counts."""
    counts = {"projects": 0, "mentions": 0, "metrics": 0, "funding_rounds": 0}

    # --- projects ---
    for proj in result.projects:
        try:
            project_id = writer.upsert_project(proj)
            counts["projects"] += 1
            if project_id:
                writer.insert_discovery("project", project_id)
        except Exception as e:
            logger.warning("Failed to upsert project %s: %s", proj.get("name"), e)

    # --- social mentions ---
    for mention in result.mentions:
        try:
            mapped = _map_mention(mention)
            url = mapped.get("url", "")
            if url and writer.is_duplicate_url(url):
                continue
            mention_id = writer.insert_social_mention(mapped)
            if mention_id:
                counts["mentions"] += 1
                writer.insert_discovery("social_mention", mention_id)
                linked = _link_mention_project(writer, mapped)
                if linked:
                    writer.link_mention_to_project(mention_id, linked)
        except Exception as e:
            logger.warning("Failed to insert mention: %s", e)

    # --- metrics ---
    for metric in result.metrics:
        try:
            if scanner.name in _GITHUB_METRIC_SCANNERS:
                mapped = _map_github_metric(metric)
                project_name = metric.get("project_name", "")
                pid = writer.find_project_id_by_name(project_name)
                if not pid and "/" in project_name:
                    pid = writer.find_project_id_by_github_org(project_name.split("/")[0])
                if pid:
                    mapped["project_id"] = pid
                writer.insert_github_metrics(mapped)
            else:
                mapped = _map_protocol_metric(metric)
                pid = writer.find_project_id_by_name(metric.get("project_name", ""))
                if pid:
                    mapped["project_id"] = pid
                writer.insert_protocol_metrics(mapped)
            counts["metrics"] += 1
        except Exception as e:
            logger.warning("Failed to insert metric: %s", e)

    # --- funding rounds ---
    for fr in result.funding_rounds:
        try:
            fr_id = writer.insert_funding_round(fr)
            if fr_id:
                counts["funding_rounds"] += 1
                writer.insert_discovery("funding_round", fr_id)
        except Exception as e:
            logger.warning("Failed to insert funding round: %s", e)

    return counts


def _run(scanners: list) -> Dict[str, Any]:
    writer = get_writer()
    summary: Dict[str, Any] = {}
    try:
        for scanner in scanners:
            started_at = datetime.utcnow().isoformat()
            try:
                logger.info("Running scanner: %s", scanner.name)
                result = scanner.scan()
                finished_at = datetime.utcnow().isoformat()
                counts = _process_scan_result(scanner, result, writer)
                total_items = sum(counts.values())
                writer.log_scan(
                    scanner.name, started_at, finished_at, "success", total_items
                )
                summary[scanner.name] = {"status": "success", **counts}
                logger.info("Scanner %s finished: %s", scanner.name, counts)
            except Exception as exc:
                finished_at = datetime.utcnow().isoformat()
                error_msg = str(exc)
                logger.exception("Scanner %s failed: %s", scanner.name, error_msg)
                writer.log_scan(
                    scanner.name, started_at, finished_at, "error", 0, error_msg
                )
                summary[scanner.name] = {"status": "error", "error": error_msg}
    finally:
        writer.close()
    return summary


def run_all_scanners() -> Dict[str, Any]:
    """Execute every registered scanner and persist results."""
    return _run([cls() for cls in _SCANNER_CLASSES])


def run_single_scanner(scanner_name: str) -> Dict[str, Any]:
    """Execute a single scanner by name."""
    for cls in _SCANNER_CLASSES:
        if cls().name == scanner_name:
            return _run([cls()])
    available = [cls().name for cls in _SCANNER_CLASSES]
    raise ValueError(f"Unknown scanner '{scanner_name}'. Available: {available}")


def _narratives_enabled() -> bool:
    """Feature flag gate for the weekly narratives job.

    Reads NARRATIVES_ENABLED directly from the process env (rather than the
    pydantic settings object) so the flag can be flipped without a config
    migration. Default is false — narratives are an opt-in, paid-API feature.
    """
    val = os.environ.get("NARRATIVES_ENABLED", "").strip().lower()
    return val in ("1", "true", "yes", "on")


def run_weekly_narratives() -> Dict[str, Any]:
    """Generate narratives for the current week (Monday-anchored).

    Fires on Mondays; pulls the previous 7 days of social_mentions, clusters
    them via Claude, and writes results to the `narratives` table. Gated
    behind the NARRATIVES_ENABLED env flag — called from scheduler cron
    AND available as a manual entrypoint via `--narratives`.
    """
    if not _narratives_enabled():
        logger.info(
            "NARRATIVES_ENABLED is not set; skipping weekly narratives job."
        )
        return {"status": "skipped", "reason": "flag_disabled"}

    # Week start = the most recent Monday (today if today is Monday).
    today = date.today()
    week_start = today - timedelta(days=today.weekday())

    writer = get_writer()
    try:
        narratives = generate_weekly_narratives(writer, week_start)
        logger.info(
            "Weekly narratives job finished: %d themes for week %s",
            len(narratives), week_start.isoformat(),
        )
        return {
            "status": "success",
            "week_start": week_start.isoformat(),
            "count": len(narratives),
        }
    except Exception as exc:
        logger.exception("Weekly narratives job failed: %s", exc)
        return {"status": "error", "error": str(exc)}
    finally:
        try:
            writer.close()
        except Exception:  # noqa: S110 — close is best-effort
            pass


def start_scheduler() -> BackgroundScheduler:
    """Create and start a BackgroundScheduler running weekly scans."""
    scheduler = BackgroundScheduler()
    trigger = CronTrigger(
        day_of_week=settings.scan_day,
        hour=settings.scan_hour,
        minute=settings.scan_minute,
    )
    scheduler.add_job(run_all_scanners, trigger=trigger, id="weekly_scan")

    # Weekly narrative clustering — Mondays at 07:00 UTC (just after the
    # normal weekly scan). Only registers when the feature flag is on, but
    # the job itself also checks the flag so hot-toggling is safe.
    if _narratives_enabled():
        scheduler.add_job(
            run_weekly_narratives,
            trigger=CronTrigger(day_of_week="mon", hour=7, minute=0),
            id="weekly_narratives",
        )
        logger.info("Weekly narratives job registered (Mondays 07:00 UTC).")
    else:
        logger.info(
            "NARRATIVES_ENABLED is off — weekly narratives job not registered."
        )

    scheduler.start()
    logger.info(
        "Scheduler started. Scans scheduled at day=%s hour=%s minute=%s",
        settings.scan_day, settings.scan_hour, settings.scan_minute,
    )
    return scheduler


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Intent-based DeFi OSINT scan orchestrator"
    )
    parser.add_argument("--once", action="store_true",
                        help="Run all scanners once and exit")
    parser.add_argument("--scanner", type=str, default=None,
                        help="Run a single scanner by name and exit")
    parser.add_argument("--narratives", action="store_true",
                        help="Run the weekly narratives job once and exit "
                             "(requires NARRATIVES_ENABLED + ANTHROPIC_API_KEY)")
    args = parser.parse_args()

    if args.scanner:
        print(run_single_scanner(args.scanner))
    elif args.narratives:
        print(run_weekly_narratives())
    elif args.once:
        print(run_all_scanners())
    else:
        start_scheduler()
        try:
            while True:
                time.sleep(60)
        except (KeyboardInterrupt, SystemExit):
            logger.info("Scheduler stopped.")
