"""
Scan orchestrator for the intent-based DeFi OSINT tracker.

Coordinates all scanners, persists results, deduplicates mentions,
and optionally runs on a weekly schedule via APScheduler.
"""

import argparse
import json
import logging
import time
from datetime import datetime
from typing import Dict, Any

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

# Scanners
from scanners.defillama import DefiLlamaScanner
from scanners.coingecko import CoinGeckoScanner
from scanners.reddit import RedditScanner
from scanners.rss import RSSScanner
from scanners.google_news import GoogleNewsScanner
from scanners.github_scanner import GitHubScanner
from scanners.blogs import BlogScanner

# Conditional import for Dune scanner (requires API key)
from core.config import settings as _settings
if _settings.dune_api_key:
    from scanners.dune import DuneScanner
else:
    DuneScanner = None

# Database
from core.db import init_db, get_connection
from core.queries import (
    upsert_project,
    insert_funding_round,
    insert_social_mention,
    insert_github_metrics,
    insert_protocol_metrics,
    log_scan,
    insert_discovery,
)

# Processing
from processing.dedup import is_duplicate_url, normalize_url
from processing.enrichment import link_mention_to_project

# Config
from core.config import settings

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)

# Scanner classes that produce github metrics (use insert_github_metrics)
_GITHUB_METRIC_SCANNERS = {"github"}

# All available scanner classes keyed by their .name attribute
_SCANNER_CLASSES = [
    DefiLlamaScanner,
    CoinGeckoScanner,
    RedditScanner,
    RSSScanner,
    GoogleNewsScanner,
    GitHubScanner,
    BlogScanner,
]

# Add Dune scanner only if the API key is configured
if DuneScanner is not None:
    _SCANNER_CLASSES.append(DuneScanner)


def _map_github_metric(raw: dict) -> dict:
    """Map scanner output keys to github_metrics DB columns."""
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
    """Map scanner output keys to protocol_metrics DB columns."""
    today = datetime.utcnow().strftime("%Y-%m-%d")
    return {
        "tvl_usd": raw.get("tvl"),
        "volume_24h": raw.get("volume_24h"),
        "chain": json.dumps(raw["chains"]) if isinstance(raw.get("chains"), list) else raw.get("chain"),
        "snapshot_date": today,
        "source": raw.get("source", ""),
    }


def _map_mention(raw: dict) -> dict:
    """Map scanner output keys to social_mentions DB columns."""
    return {
        "source": raw.get("source", ""),
        "title": raw.get("title", ""),
        "url": raw.get("url") or raw.get("link", ""),
        "author": raw.get("author", ""),
        "content_snippet": raw.get("content_snippet") or raw.get("text") or raw.get("snippet", ""),
        "sentiment_score": raw.get("sentiment_score"),
        "upvotes": raw.get("upvotes") or raw.get("score", 0),
        "published_at": raw.get("published_at") or raw.get("published", ""),
    }


def _process_scan_result(scanner, result, conn) -> Dict[str, int]:
    """Persist a ScanResult into the database, returning per-entity counts."""
    counts = {
        "projects": 0,
        "mentions": 0,
        "metrics": 0,
        "funding_rounds": 0,
    }

    # --- projects ---
    for proj in result.projects:
        try:
            project_id = upsert_project(conn, proj)
            counts["projects"] += 1
            if project_id:
                insert_discovery(conn, "project", project_id)
        except Exception as e:
            logger.warning("Failed to upsert project %s: %s", proj.get("name"), e)

    # --- social mentions ---
    for mention in result.mentions:
        try:
            mapped = _map_mention(mention)
            url = mapped.get("url", "")
            if url and is_duplicate_url(conn, url):
                continue
            mention_id = insert_social_mention(conn, mapped)
            if mention_id:
                counts["mentions"] += 1
                insert_discovery(conn, "social_mention", mention_id)
                # Try to link mention to a known project
                project_id = link_mention_to_project(conn, mapped)
                if project_id:
                    conn.execute(
                        "UPDATE social_mentions SET project_id = ? WHERE id = ?",
                        (project_id, mention_id),
                    )
                    conn.commit()
        except Exception as e:
            logger.warning("Failed to insert mention: %s", e)

    # --- metrics ---
    for metric in result.metrics:
        try:
            if scanner.name in _GITHUB_METRIC_SCANNERS:
                mapped = _map_github_metric(metric)
                # Link to project: try exact name, then org match
                project_name = metric.get("project_name", "")
                row = conn.execute(
                    "SELECT id FROM projects WHERE name = ?",
                    (project_name,),
                ).fetchone()
                if not row and "/" in project_name:
                    org = project_name.split("/")[0]
                    row = conn.execute(
                        "SELECT id FROM projects WHERE github_org = ?",
                        (org,),
                    ).fetchone()
                if row:
                    mapped["project_id"] = row[0]
                insert_github_metrics(conn, mapped)
            else:
                mapped = _map_protocol_metric(metric)
                # Link to project by name
                row = conn.execute(
                    "SELECT id FROM projects WHERE name = ?",
                    (metric.get("project_name"),),
                ).fetchone()
                if row:
                    mapped["project_id"] = row[0]
                insert_protocol_metrics(conn, mapped)
            counts["metrics"] += 1
        except Exception as e:
            logger.warning("Failed to insert metric: %s", e)

    # --- funding rounds ---
    for fr in result.funding_rounds:
        try:
            fr_id = insert_funding_round(conn, fr)
            if fr_id:
                counts["funding_rounds"] += 1
                insert_discovery(conn, "funding_round", fr_id)
        except Exception as e:
            logger.warning("Failed to insert funding round: %s", e)

    return counts


def run_all_scanners() -> Dict[str, Any]:
    """Execute every registered scanner and persist results.

    Returns a summary dict mapping scanner names to their result counts.
    """
    init_db()
    conn = get_connection()
    summary: Dict[str, Any] = {}

    scanners = [cls() for cls in _SCANNER_CLASSES]

    for scanner in scanners:
        started_at = datetime.utcnow().isoformat()
        try:
            logger.info("Running scanner: %s", scanner.name)
            result = scanner.scan()
            finished_at = datetime.utcnow().isoformat()

            counts = _process_scan_result(scanner, result, conn)
            total_items = sum(counts.values())

            log_scan(
                conn,
                scanner_name=scanner.name,
                started_at=started_at,
                finished_at=finished_at,
                status="success",
                items_found=total_items,
            )

            summary[scanner.name] = {"status": "success", **counts}
            logger.info("Scanner %s finished: %s", scanner.name, counts)

        except Exception as exc:
            finished_at = datetime.utcnow().isoformat()
            error_msg = str(exc)
            logger.exception("Scanner %s failed: %s", scanner.name, error_msg)

            log_scan(
                conn,
                scanner_name=scanner.name,
                started_at=started_at,
                finished_at=finished_at,
                status="error",
                items_found=0,
                error_message=error_msg,
            )

            summary[scanner.name] = {"status": "error", "error": error_msg}

    conn.close()
    return summary


def run_single_scanner(scanner_name: str) -> Dict[str, Any]:
    """Execute a single scanner by name and persist its results.

    Raises ValueError if the scanner name is not recognised.
    """
    init_db()
    conn = get_connection()

    # Find the matching scanner class
    scanner_cls = None
    for cls in _SCANNER_CLASSES:
        instance = cls()
        if instance.name == scanner_name:
            scanner_cls = cls
            break

    if scanner_cls is None:
        available = [cls().name for cls in _SCANNER_CLASSES]
        raise ValueError(
            f"Unknown scanner '{scanner_name}'. Available: {available}"
        )

    scanner = scanner_cls()
    started_at = datetime.utcnow().isoformat()

    try:
        logger.info("Running single scanner: %s", scanner.name)
        result = scanner.scan()
        finished_at = datetime.utcnow().isoformat()

        counts = _process_scan_result(scanner, result, conn)
        total_items = sum(counts.values())

        log_scan(
            conn,
            scanner_name=scanner.name,
            started_at=started_at,
            finished_at=finished_at,
            status="success",
            items_found=total_items,
        )

        summary = {scanner.name: {"status": "success", **counts}}
        logger.info("Scanner %s finished: %s", scanner.name, counts)

    except Exception as exc:
        finished_at = datetime.utcnow().isoformat()
        error_msg = str(exc)
        logger.exception("Scanner %s failed: %s", scanner.name, error_msg)

        log_scan(
            conn,
            scanner_name=scanner.name,
            started_at=started_at,
            finished_at=finished_at,
            status="error",
            items_found=0,
            error_message=error_msg,
        )

        summary = {scanner.name: {"status": "error", "error": error_msg}}

    conn.close()
    return summary


def start_scheduler() -> BackgroundScheduler:
    """Create and start a BackgroundScheduler running weekly scans.

    Schedule is controlled by config.settings.scan_day / SCAN_HOUR / SCAN_MINUTE.
    """
    scheduler = BackgroundScheduler()

    trigger = CronTrigger(
        day_of_week=settings.scan_day,
        hour=settings.scan_hour,
        minute=settings.scan_minute,
    )

    scheduler.add_job(run_all_scanners, trigger=trigger, id="weekly_scan")
    scheduler.start()

    logger.info(
        "Scheduler started. Scans scheduled at day=%s hour=%s minute=%s",
        settings.scan_day,
        settings.scan_hour,
        settings.scan_minute,
    )

    return scheduler


# ---------------------------------------------------------------------------
# CLI entry-point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Intent-based DeFi OSINT scan orchestrator"
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run all scanners once and exit (no scheduling)",
    )
    parser.add_argument(
        "--scanner",
        type=str,
        default=None,
        help="Run a single scanner by name and exit",
    )
    args = parser.parse_args()

    if args.scanner:
        result = run_single_scanner(args.scanner)
        print(result)
    elif args.once:
        result = run_all_scanners()
        print(result)
    else:
        start_scheduler()
        try:
            while True:
                time.sleep(60)
        except (KeyboardInterrupt, SystemExit):
            logger.info("Scheduler stopped.")
