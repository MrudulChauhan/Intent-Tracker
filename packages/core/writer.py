"""Unified write interface for the scanner.

Routes writes to either:
  - SupabaseWriter (if SUPABASE_URL + SUPABASE_SERVICE_KEY are set)
  - SQLiteWriter   (the local dev fallback)

`scheduler.py` only knows about the `Writer` protocol below — it never touches
raw SQL or PostgREST directly. Switching between the two is a pure env-var
flip, no code changes.
"""

from __future__ import annotations

import logging
from typing import Optional, Protocol

from core.config import settings


logger = logging.getLogger(__name__)


class Writer(Protocol):
    def upsert_project(self, project: dict) -> Optional[int]: ...
    def insert_funding_round(self, round_data: dict) -> Optional[int]: ...
    def insert_social_mention(self, mention: dict) -> Optional[int]: ...
    def insert_github_metrics(self, metrics: dict) -> Optional[int]: ...
    def insert_protocol_metrics(self, metrics: dict) -> Optional[int]: ...
    def log_scan(self, scanner_name: str, started_at: str, finished_at: str,
                 status: str, items_found: int,
                 error_message: Optional[str] = None) -> Optional[int]: ...
    def insert_discovery(self, entity_type: str, entity_id: int) -> Optional[int]: ...

    def find_project_id_by_name(self, name: str) -> Optional[int]: ...
    def find_project_id_by_github_org(self, org: str) -> Optional[int]: ...
    def link_mention_to_project(self, mention_id: int, project_id: int) -> None: ...
    def is_duplicate_url(self, url: str) -> bool: ...

    def close(self) -> None: ...


class SQLiteWriter:
    """Thin adapter around core.queries + core.db for local dev."""

    def __init__(self) -> None:
        from core.db import get_connection, init_db
        init_db()
        self.conn = get_connection()

    def upsert_project(self, project):
        from core.queries import upsert_project
        return upsert_project(self.conn, project)

    def insert_funding_round(self, row):
        from core.queries import insert_funding_round
        return insert_funding_round(self.conn, row)

    def insert_social_mention(self, mention):
        from core.queries import insert_social_mention
        return insert_social_mention(self.conn, mention)

    def insert_github_metrics(self, metrics):
        from core.queries import insert_github_metrics
        return insert_github_metrics(self.conn, metrics)

    def insert_protocol_metrics(self, metrics):
        from core.queries import insert_protocol_metrics
        return insert_protocol_metrics(self.conn, metrics)

    def log_scan(self, scanner_name, started_at, finished_at, status,
                 items_found, error_message=None):
        from core.queries import log_scan
        return log_scan(self.conn, scanner_name, started_at, finished_at,
                        status, items_found, error_message)

    def insert_discovery(self, entity_type, entity_id):
        from core.queries import insert_discovery
        return insert_discovery(self.conn, entity_type, entity_id)

    def find_project_id_by_name(self, name):
        row = self.conn.execute(
            "SELECT id FROM projects WHERE name = ?", (name,)
        ).fetchone()
        return row[0] if row else None

    def find_project_id_by_github_org(self, org):
        row = self.conn.execute(
            "SELECT id FROM projects WHERE github_org = ?", (org,)
        ).fetchone()
        return row[0] if row else None

    def link_mention_to_project(self, mention_id, project_id):
        self.conn.execute(
            "UPDATE social_mentions SET project_id = ? WHERE id = ?",
            (project_id, mention_id),
        )
        self.conn.commit()

    def is_duplicate_url(self, url):
        from processing.dedup import is_duplicate_url
        return is_duplicate_url(self.conn, url)

    def close(self):
        self.conn.close()


def get_writer() -> Writer:
    """Return the active Writer: Supabase if configured, else SQLite."""
    if settings.supabase_url and settings.supabase_service_key:
        from core.supabase_writer import SupabaseWriter
        logger.info("Writer: Supabase (%s)", settings.supabase_url)
        return SupabaseWriter(settings.supabase_url, settings.supabase_service_key)
    logger.info("Writer: local SQLite (%s)", settings.db_path)
    return SQLiteWriter()
