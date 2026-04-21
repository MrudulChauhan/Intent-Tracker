"""CRUD functions for the intent-based DeFi ecosystem tracker."""

import json
import sqlite3
from typing import Optional


def _row_to_dict(row: sqlite3.Row) -> dict:
    """Convert a sqlite3.Row to a plain dict."""
    return dict(row)


def _rows_to_list(cursor: sqlite3.Cursor) -> list:
    """Fetch all rows from a cursor and return as list of dicts."""
    return [_row_to_dict(r) for r in cursor.fetchall()]


# ---------------------------------------------------------------------------
# Upsert / Insert
# ---------------------------------------------------------------------------

def upsert_project(conn: sqlite3.Connection, project: dict) -> int:
    """Insert or update a project. Returns the project id."""
    cols = [
        "name", "slug", "description", "website", "chains", "category",
        "status", "token_symbol", "coingecko_id", "defillama_slug",
        "github_org", "twitter_handle", "relevance_score", "is_manually_tracked",
    ]
    present = [c for c in cols if c in project]
    placeholders = ", ".join(["?"] * len(present))
    col_names = ", ".join(present)
    update_clause = ", ".join(f"{c}=excluded.{c}" for c in present if c != "name")

    sql = (
        f"INSERT INTO projects ({col_names}) VALUES ({placeholders}) "
        f"ON CONFLICT(name) DO UPDATE SET {update_clause}, "
        f"last_updated=CURRENT_TIMESTAMP"
    )
    values = []
    for c in present:
        v = project[c]
        # JSON-serialize lists/dicts for SQLite TEXT columns
        if isinstance(v, (list, dict)):
            v = json.dumps(v)
        values.append(v)
    cur = conn.execute(sql, values)
    conn.commit()

    # Return the id of the upserted row
    row = conn.execute(
        "SELECT id FROM projects WHERE name = ?", (project["name"],)
    ).fetchone()
    return row["id"]


def insert_funding_round(conn: sqlite3.Connection, round_data: dict) -> int:
    """Insert a funding round and return its id."""
    cols = [
        "project_id", "round_type", "amount_usd", "date",
        "lead_investor", "investors", "source_url",
    ]
    present = [c for c in cols if c in round_data]
    placeholders = ", ".join(["?"] * len(present))
    col_names = ", ".join(present)

    sql = f"INSERT INTO funding_rounds ({col_names}) VALUES ({placeholders})"
    cur = conn.execute(sql, [round_data[c] for c in present])
    conn.commit()
    return cur.lastrowid


def insert_social_mention(conn: sqlite3.Connection, mention: dict) -> int:
    """Insert a social mention (ignore if url already exists). Returns id or 0."""
    cols = [
        "project_id", "source", "title", "url", "author",
        "content_snippet", "sentiment_score", "upvotes", "published_at",
    ]
    present = [c for c in cols if c in mention]
    placeholders = ", ".join(["?"] * len(present))
    col_names = ", ".join(present)

    sql = f"INSERT OR IGNORE INTO social_mentions ({col_names}) VALUES ({placeholders})"
    cur = conn.execute(sql, [mention[c] for c in present])
    conn.commit()
    return cur.lastrowid or 0


def insert_github_metrics(conn: sqlite3.Connection, metrics: dict) -> int:
    """Insert a github metrics snapshot. Returns id."""
    cols = [
        "project_id", "repo_url", "stars", "forks", "open_issues",
        "contributors_count", "last_commit_at", "commits_30d", "snapshot_date",
    ]
    present = [c for c in cols if c in metrics]
    placeholders = ", ".join(["?"] * len(present))
    col_names = ", ".join(present)

    sql = f"INSERT INTO github_metrics ({col_names}) VALUES ({placeholders})"
    cur = conn.execute(sql, [metrics[c] for c in present])
    conn.commit()
    return cur.lastrowid


def insert_protocol_metrics(conn: sqlite3.Connection, metrics: dict) -> int:
    """Insert a protocol metrics snapshot. Returns id."""
    cols = [
        "project_id", "tvl_usd", "volume_24h", "chain",
        "snapshot_date", "source",
    ]
    present = [c for c in cols if c in metrics]
    placeholders = ", ".join(["?"] * len(present))
    col_names = ", ".join(present)

    sql = f"INSERT INTO protocol_metrics ({col_names}) VALUES ({placeholders})"
    cur = conn.execute(sql, [metrics[c] for c in present])
    conn.commit()
    return cur.lastrowid


def log_scan(
    conn: sqlite3.Connection,
    scanner_name: str,
    started_at: str,
    finished_at: str,
    status: str,
    items_found: int,
    error_message: Optional[str] = None,
) -> int:
    """Log a scan run. Returns id."""
    sql = (
        "INSERT INTO scan_log "
        "(scanner_name, started_at, finished_at, status, items_found, error_message) "
        "VALUES (?, ?, ?, ?, ?, ?)"
    )
    cur = conn.execute(
        sql, (scanner_name, started_at, finished_at, status, items_found, error_message)
    )
    conn.commit()
    return cur.lastrowid


def insert_discovery(
    conn: sqlite3.Connection, entity_type: str, entity_id: int
) -> int:
    """Record a new discovery. Returns id."""
    sql = "INSERT INTO discoveries (entity_type, entity_id) VALUES (?, ?)"
    cur = conn.execute(sql, (entity_type, entity_id))
    conn.commit()
    return cur.lastrowid


# ---------------------------------------------------------------------------
# Filter helpers
# ---------------------------------------------------------------------------

def _apply_filters(filters: Optional[dict], table_alias: str = "") -> tuple:
    """Build WHERE clauses from a dashboard filters dict.

    Handles special keys: date_from, date_to, search_query, chain, category,
    source, sentiment. Unknown keys are ignored (not passed as column names).

    Returns (clauses: list[str], params: list).
    """
    if not filters:
        return [], []

    prefix = f"{table_alias}." if table_alias else ""
    clauses = []
    params = []

    for key, value in filters.items():
        if value is None or value == "" or value == []:
            continue

        if key == "date_from":
            clauses.append(f"{prefix}last_updated >= ?")
            params.append(str(value) + " 00:00:00")
        elif key == "date_to":
            clauses.append(f"{prefix}last_updated <= ?")
            params.append(str(value) + " 23:59:59")
        elif key == "search_query":
            clauses.append(f"({prefix}name LIKE ? OR {prefix}description LIKE ?)")
            params.extend([f"%{value}%", f"%{value}%"])
        elif key == "chain":
            # chains is a JSON array stored as text — use LIKE for each selected chain
            if isinstance(value, list):
                chain_clauses = [f"{prefix}chains LIKE ?" for _ in value]
                clauses.append(f"({' OR '.join(chain_clauses)})")
                params.extend([f"%{c}%" for c in value])
            else:
                clauses.append(f"{prefix}chains LIKE ?")
                params.append(f"%{value}%")
        elif key == "category":
            if isinstance(value, list):
                placeholders = ", ".join(["?"] * len(value))
                clauses.append(f"{prefix}category IN ({placeholders})")
                params.extend(value)
            else:
                clauses.append(f"{prefix}category = ?")
                params.append(value)
        elif key == "source":
            if isinstance(value, list):
                placeholders = ", ".join(["?"] * len(value))
                clauses.append(f"{prefix}source IN ({placeholders})")
                params.extend(value)
            else:
                clauses.append(f"{prefix}source = ?")
                params.append(value)
        # Ignore unknown keys silently

    return clauses, params


def _apply_mention_filters(filters: Optional[dict]) -> tuple:
    """Build WHERE clauses for social_mentions table."""
    if not filters:
        return [], []

    clauses = []
    params = []

    for key, value in filters.items():
        if value is None or value == "" or value == []:
            continue

        if key == "date_from":
            clauses.append("discovered_at >= ?")
            params.append(str(value) + " 00:00:00")
        elif key == "date_to":
            clauses.append("discovered_at <= ?")
            params.append(str(value) + " 23:59:59")
        elif key == "search_query":
            clauses.append("(title LIKE ? OR content_snippet LIKE ?)")
            params.extend([f"%{value}%", f"%{value}%"])
        elif key == "source":
            if isinstance(value, list):
                placeholders = ", ".join(["?"] * len(value))
                clauses.append(f"source IN ({placeholders})")
                params.extend(value)
            else:
                clauses.append("source = ?")
                params.append(value)

    return clauses, params


# ---------------------------------------------------------------------------
# Read / Query
# ---------------------------------------------------------------------------

def get_all_projects(
    conn: sqlite3.Connection, filters: Optional[dict] = None
) -> list:
    """Return all projects, optionally filtered."""
    sql = "SELECT * FROM projects"
    clauses, params = _apply_filters(filters)
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY relevance_score DESC"
    return _rows_to_list(conn.execute(sql, params))


def get_project_by_name(conn: sqlite3.Connection, name: str):
    """Return a single project dict or None."""
    row = conn.execute("SELECT * FROM projects WHERE name = ?", (name,)).fetchone()
    return _row_to_dict(row) if row else None


def get_funding_rounds(
    conn: sqlite3.Connection, filters: Optional[dict] = None
) -> list:
    """Return funding rounds, optionally filtered."""
    sql = """
        SELECT fr.*, p.name AS project_name
        FROM funding_rounds fr
        LEFT JOIN projects p ON p.id = fr.project_id
    """
    clauses, params = _apply_filters(filters, table_alias="p")
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY fr.date DESC"
    return _rows_to_list(conn.execute(sql, params))


def get_social_mentions(
    conn: sqlite3.Connection, filters: Optional[dict] = None
) -> list:
    """Return social mentions, optionally filtered."""
    sql = "SELECT * FROM social_mentions"
    clauses, params = _apply_mention_filters(filters)
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY discovered_at DESC"
    return _rows_to_list(conn.execute(sql, params))


def get_github_metrics(
    conn: sqlite3.Connection, filters: Optional[dict] = None
) -> list:
    """Return github metrics, optionally filtered."""
    sql = "SELECT * FROM github_metrics"
    params = []
    sql += " ORDER BY snapshot_date DESC"
    return _rows_to_list(conn.execute(sql, params))


def get_protocol_metrics(
    conn: sqlite3.Connection, project_id: Optional[int] = None
) -> list:
    """Return protocol metrics, optionally filtered by project_id."""
    sql = "SELECT * FROM protocol_metrics"
    params = []
    if project_id is not None:
        sql += " WHERE project_id = ?"
        params.append(project_id)
    sql += " ORDER BY snapshot_date DESC"
    return _rows_to_list(conn.execute(sql, params))


def get_discoveries(
    conn: sqlite3.Connection, reviewed: Optional[int] = None
) -> list:
    """Return discoveries with entity names resolved via joins."""
    sql = """
        SELECT
            d.id,
            d.entity_type,
            d.entity_id,
            d.discovered_at,
            d.reviewed,
            CASE
                WHEN d.entity_type = 'project' THEN p.name
                WHEN d.entity_type = 'social_mention' THEN sm.title
                WHEN d.entity_type = 'funding_round' THEN fr_p.name
                ELSE 'Unknown'
            END AS name,
            CASE
                WHEN d.entity_type = 'project' THEN p.category
                WHEN d.entity_type = 'social_mention' THEN sm.source
                WHEN d.entity_type = 'funding_round' THEN fr.round_type
                ELSE NULL
            END AS detail
        FROM discoveries d
        LEFT JOIN projects p ON d.entity_type = 'project' AND d.entity_id = p.id
        LEFT JOIN social_mentions sm ON d.entity_type = 'social_mention' AND d.entity_id = sm.id
        LEFT JOIN funding_rounds fr ON d.entity_type = 'funding_round' AND d.entity_id = fr.id
        LEFT JOIN projects fr_p ON fr.project_id = fr_p.id
    """
    params = []
    if reviewed is not None:
        reviewed_val = int(reviewed) if isinstance(reviewed, bool) else reviewed
        sql += " WHERE d.reviewed = ?"
        params.append(reviewed_val)
    sql += " ORDER BY d.discovered_at DESC"
    return _rows_to_list(conn.execute(sql, params))


def get_scan_log(conn: sqlite3.Connection, limit: int = 20) -> list:
    """Return recent scan log entries."""
    sql = "SELECT * FROM scan_log ORDER BY started_at DESC LIMIT ?"
    return _rows_to_list(conn.execute(sql, (limit,)))


def mark_discovery_reviewed(conn: sqlite3.Connection, discovery_id: int) -> None:
    """Mark a discovery as reviewed."""
    conn.execute("UPDATE discoveries SET reviewed = 1 WHERE id = ?", (discovery_id,))
    conn.commit()


def get_network_data(conn: sqlite3.Connection) -> list:
    """Join projects, people, and funding rounds for a network view."""
    sql = """
        SELECT
            p.id AS project_id,
            p.name AS project_name,
            p.category,
            p.chains,
            p.relevance_score,
            pe.name AS person_name,
            pe.role AS person_role,
            fr.round_type,
            fr.amount_usd,
            fr.lead_investor,
            fr.investors,
            fr.date AS funding_date
        FROM projects p
        LEFT JOIN people pe ON pe.project_id = p.id
        LEFT JOIN funding_rounds fr ON fr.project_id = p.id
        ORDER BY p.relevance_score DESC, fr.date DESC
    """
    return _rows_to_list(conn.execute(sql))


def search_projects(conn: sqlite3.Connection, query: str) -> list:
    """Search projects by name or description (case-insensitive LIKE)."""
    like = f"%{query}%"
    sql = """
        SELECT * FROM projects
        WHERE name LIKE ? OR description LIKE ? OR category LIKE ?
        ORDER BY relevance_score DESC
    """
    return _rows_to_list(conn.execute(sql, (like, like, like)))
