"""Supabase write adapter for the scanner.

Mirrors the write-side of `core/queries.py` (upsert_project, insert_*) but
targets the Supabase Postgres instance via PostgREST + service_role.

The scanner code path remains unchanged; `scheduler/scheduler.py` passes a
`Writer` into `_process_scan_result` and it decides where the row goes based
on `settings.supabase_url`.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, Optional

import httpx

from core.config import settings


logger = logging.getLogger(__name__)


def _iso(value: Any) -> Any:
    """Serialize datetimes and lists for JSON transport."""
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, (list, dict)):
        return json.dumps(value) if isinstance(value, list) and value and isinstance(value[0], str) is False else value
    return value


def _json_safe(row: dict) -> dict:
    """Make a dict safe to POST — lists become JSON strings for TEXT cols,
    dicts stay as JSON (Postgres jsonb handles them), datetimes → ISO."""
    out = {}
    for k, v in row.items():
        if isinstance(v, datetime):
            out[k] = v.isoformat()
        elif isinstance(v, list):
            # chains / investors are stored as jsonb in Postgres
            out[k] = v
        elif isinstance(v, dict):
            out[k] = v
        else:
            out[k] = v
    return out


class SupabaseWriter:
    """Thin PostgREST client targeting the intent-tracker Supabase project."""

    def __init__(self, url: str, service_key: str):
        if not url or not service_key:
            raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY must both be set")
        self.base = url.rstrip("/") + "/rest/v1"
        self.headers = {
            "apikey": service_key,
            "Authorization": f"Bearer {service_key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }
        self.client = httpx.Client(timeout=30.0, headers=self.headers)

    # ---- low-level ------------------------------------------------------

    def _post(self, table: str, row: dict, *, on_conflict: Optional[str] = None,
              ignore_duplicates: bool = False) -> Optional[dict]:
        url = f"{self.base}/{table}"
        params = {}
        headers = dict(self.headers)
        if on_conflict:
            params["on_conflict"] = on_conflict
            headers["Prefer"] = (
                "return=representation,resolution=ignore-duplicates"
                if ignore_duplicates
                else "return=representation,resolution=merge-duplicates"
            )
        elif ignore_duplicates:
            headers["Prefer"] = "return=representation,resolution=ignore-duplicates"

        resp = self.client.post(url, params=params, headers=headers, json=_json_safe(row))
        if resp.status_code >= 400:
            logger.warning(
                "Supabase POST %s failed (%d): %s", table, resp.status_code, resp.text[:200]
            )
            return None
        data = resp.json()
        return data[0] if isinstance(data, list) and data else data

    def _patch_by_id(self, table: str, row_id: int, patch: dict) -> None:
        url = f"{self.base}/{table}"
        resp = self.client.patch(
            url, params={"id": f"eq.{row_id}"}, json=_json_safe(patch)
        )
        if resp.status_code >= 400:
            logger.warning(
                "Supabase PATCH %s id=%s failed (%d): %s",
                table, row_id, resp.status_code, resp.text[:200],
            )

    def _get_one(self, table: str, **eq) -> Optional[dict]:
        url = f"{self.base}/{table}"
        params = {f"{k}": f"eq.{v}" for k, v in eq.items()}
        params["limit"] = "1"
        resp = self.client.get(url, params=params)
        if resp.status_code >= 400:
            return None
        data = resp.json()
        return data[0] if data else None

    # ---- table-specific -------------------------------------------------

    _PROJECT_COLS = [
        "name", "slug", "description", "website", "chains", "category",
        "role", "intent_type",
        "status", "token_symbol", "coingecko_id", "defillama_slug",
        "github_org", "twitter_handle", "relevance_score", "is_manually_tracked",
    ]

    def upsert_project(self, project: dict) -> Optional[int]:
        row = {k: project[k] for k in self._PROJECT_COLS if k in project}
        # chains may come in as a JSON string from SQLite — normalize to list
        if isinstance(row.get("chains"), str):
            try:
                row["chains"] = json.loads(row["chains"])
            except (json.JSONDecodeError, TypeError):
                row["chains"] = None
        # Auto-classify to (role, intent_type) when the scanner only supplied
        # the legacy `category`. Prevents drift like "Dexs"/"DEX" re-entering.
        if ("role" not in row or "intent_type" not in row) and row.get("category"):
            from core.taxonomy import classify
            role, intent_type = classify(row["category"])
            row.setdefault("role", role)
            row.setdefault("intent_type", intent_type)
        row["last_updated"] = datetime.utcnow().isoformat()
        result = self._post("projects", row, on_conflict="name")
        if result:
            return result.get("id")
        # fallback: fetch by name
        existing = self._get_one("projects", name=project.get("name", ""))
        return existing.get("id") if existing else None

    def insert_funding_round(self, round_data: dict) -> Optional[int]:
        cols = [
            "project_id", "round_type", "amount_usd", "date",
            "lead_investor", "investors", "source_url",
        ]
        row = {k: round_data[k] for k in cols if k in round_data}
        if isinstance(row.get("investors"), str):
            try:
                row["investors"] = json.loads(row["investors"])
            except (json.JSONDecodeError, TypeError):
                row["investors"] = None
        result = self._post("funding_rounds", row)
        return result.get("id") if result else None

    def insert_social_mention(self, mention: dict) -> Optional[int]:
        cols = [
            "project_id", "source", "title", "url", "author",
            "content_snippet", "sentiment_score", "upvotes", "published_at",
        ]
        row = {k: mention[k] for k in cols if k in mention}
        result = self._post("social_mentions", row, on_conflict="url",
                            ignore_duplicates=True)
        return result.get("id") if result else 0

    def insert_github_metrics(self, metrics: dict) -> Optional[int]:
        cols = [
            "project_id", "repo_url", "stars", "forks", "open_issues",
            "contributors_count", "last_commit_at", "commits_30d", "snapshot_date",
        ]
        row = {k: metrics[k] for k in cols if k in metrics}
        result = self._post("github_metrics", row)
        return result.get("id") if result else None

    def insert_protocol_metrics(self, metrics: dict) -> Optional[int]:
        cols = ["project_id", "tvl_usd", "volume_24h", "chain",
                "snapshot_date", "source"]
        row = {k: metrics[k] for k in cols if k in metrics}
        result = self._post("protocol_metrics", row)
        return result.get("id") if result else None

    def log_scan(self, scanner_name: str, started_at: str, finished_at: str,
                 status: str, items_found: int,
                 error_message: Optional[str] = None) -> Optional[int]:
        row = {
            "scanner_name": scanner_name,
            "started_at": started_at,
            "finished_at": finished_at,
            "status": status,
            "items_found": items_found,
            "error_message": error_message,
        }
        result = self._post("scan_log", row)
        return result.get("id") if result else None

    def insert_discovery(self, entity_type: str, entity_id: int) -> Optional[int]:
        result = self._post(
            "discoveries", {"entity_type": entity_type, "entity_id": entity_id}
        )
        return result.get("id") if result else None

    # ---- helpers used by scheduler --------------------------------------

    def find_project_id_by_name(self, name: str) -> Optional[int]:
        existing = self._get_one("projects", name=name)
        return existing.get("id") if existing else None

    def find_project_id_by_github_org(self, org: str) -> Optional[int]:
        existing = self._get_one("projects", github_org=org)
        return existing.get("id") if existing else None

    def link_mention_to_project(self, mention_id: int, project_id: int) -> None:
        self._patch_by_id("social_mentions", mention_id, {"project_id": project_id})

    def is_duplicate_url(self, url: str) -> bool:
        existing = self._get_one("social_mentions", url=url)
        return existing is not None

    def close(self) -> None:
        """Close the underlying httpx client. Matches the Writer protocol."""
        self.client.close()


def get_writer() -> Optional[SupabaseWriter]:
    """Return a SupabaseWriter if Supabase env vars are set, else None.

    When None, callers fall back to SQLite via core.db.get_connection().
    """
    if settings.supabase_url and settings.supabase_service_key:
        return SupabaseWriter(settings.supabase_url, settings.supabase_service_key)
    return None
