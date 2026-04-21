"""FastAPI backend for intent-tracker."""

import subprocess
import sys
from datetime import datetime, timedelta
from typing import Optional

import time
from collections import deque
from threading import Lock

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from apps.api.solvers_data import SOLVERS_DATA
from core.config import settings
from core.db import get_connection
from core.paths import REPO_ROOT
from core.queries import (
    get_all_projects,
    get_discoveries,
    get_github_metrics,
    get_protocol_metrics,
    get_scan_log,
    get_social_mentions,
    mark_discovery_reviewed,
    search_projects,
)

app = FastAPI(title="Intent Tracker API", version="0.2.0")

# CORS — origins are resolved from settings.get_allowed_origins() which:
#   dev:          localhost:WEB_PORT + 127.0.0.1:WEB_PORT by default
#   staging/prod: ALLOWED_ORIGINS env (fail closed if unset)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_allowed_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization", "X-Scan-Token"],
)


# ---------------------------------------------------------------------------
# Auth + rate limiting for /api/scan
# ---------------------------------------------------------------------------
_SCAN_WINDOW_SECONDS = 60
_SCAN_MAX_PER_WINDOW = 3
_scan_hits: deque[float] = deque(maxlen=_SCAN_MAX_PER_WINDOW * 4)
_scan_hits_lock = Lock()


def _rate_limit_scan() -> None:
    """Simple in-memory token bucket: max N scans per window."""
    now = time.monotonic()
    with _scan_hits_lock:
        while _scan_hits and now - _scan_hits[0] > _SCAN_WINDOW_SECONDS:
            _scan_hits.popleft()
        if len(_scan_hits) >= _SCAN_MAX_PER_WINDOW:
            retry_after = int(_SCAN_WINDOW_SECONDS - (now - _scan_hits[0]))
            raise HTTPException(
                status_code=429,
                detail=f"Scan rate limit exceeded — retry in {retry_after}s",
            )
        _scan_hits.append(now)


def require_scan_auth(x_scan_token: str | None = Header(default=None)) -> None:
    """Require an X-Scan-Token header matching settings.scan_token.

    In dev with no SCAN_TOKEN configured, the check is skipped (preserves
    local-only convenience). In staging/production the pydantic validator
    enforces a non-empty SCAN_TOKEN at boot.
    """
    expected = settings.scan_token
    if settings.environment == "dev" and not expected:
        return
    if not x_scan_token or x_scan_token != expected:
        raise HTTPException(status_code=401, detail="Invalid or missing X-Scan-Token")


@app.get("/api/projects")
def list_projects(
    search: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[str] = None,
    chain: Optional[str] = None,
):
    """Return all projects with optional filtering."""
    conn = get_connection()
    try:
        if search:
            results = search_projects(conn, search)
            # Apply additional filters on search results
            if category:
                results = [p for p in results if p.get("category") == category]
            if status:
                results = [p for p in results if p.get("status") == status]
            if chain:
                results = [p for p in results if chain in (p.get("chains") or "")]
            return results
        else:
            filters = {}
            if category:
                filters["category"] = category
            if chain:
                filters["chain"] = chain
            results = get_all_projects(conn, filters if filters else None)
            if status:
                results = [p for p in results if p.get("status") == status]
            return results
    finally:
        conn.close()


@app.get("/api/projects/{project_id}")
def get_project(project_id: int):
    """Return a single project with its protocol metrics."""
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Project not found")
        project = dict(row)
        project["protocol_metrics"] = get_protocol_metrics(conn, project_id)
        return project
    finally:
        conn.close()


@app.get("/api/mentions/stats")
def mentions_stats():
    """Return mention statistics."""
    conn = get_connection()
    try:
        total = conn.execute("SELECT COUNT(*) as cnt FROM social_mentions").fetchone()["cnt"]

        by_source_rows = conn.execute(
            "SELECT source, COUNT(*) as cnt FROM social_mentions GROUP BY source"
        ).fetchall()
        by_source = {row["source"]: row["cnt"] for row in by_source_rows}

        one_week_ago = (datetime.utcnow() - timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
        this_week = conn.execute(
            "SELECT COUNT(*) as cnt FROM social_mentions WHERE discovered_at >= ?",
            (one_week_ago,),
        ).fetchone()["cnt"]

        return {"total": total, "by_source": by_source, "this_week": this_week}
    finally:
        conn.close()


@app.get("/api/mentions")
def list_mentions(
    source: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = Query(default=100, ge=1, le=1000),
):
    """Return social mentions."""
    conn = get_connection()
    try:
        filters = {}
        if source:
            filters["source"] = source
        if search:
            filters["search_query"] = search
        results = get_social_mentions(conn, filters if filters else None)
        return results[:limit]
    finally:
        conn.close()


@app.get("/api/github")
def list_github():
    """Return github metrics."""
    conn = get_connection()
    try:
        return get_github_metrics(conn)
    finally:
        conn.close()


@app.get("/api/discoveries")
def list_discoveries(
    reviewed: Optional[int] = None,
    type: Optional[str] = None,
):
    """Return discoveries."""
    conn = get_connection()
    try:
        results = get_discoveries(conn, reviewed=reviewed)
        if type:
            results = [d for d in results if d.get("entity_type") == type]
        return results
    finally:
        conn.close()


@app.post("/api/discoveries/{discovery_id}/review")
def review_discovery(discovery_id: int):
    """Mark a discovery as reviewed."""
    conn = get_connection()
    try:
        row = conn.execute("SELECT id FROM discoveries WHERE id = ?", (discovery_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Discovery not found")
        mark_discovery_reviewed(conn, discovery_id)
        return {"status": "ok", "id": discovery_id, "reviewed": 1}
    finally:
        conn.close()


@app.get("/api/scan-log")
def list_scan_log():
    """Return scan log entries."""
    conn = get_connection()
    try:
        return get_scan_log(conn)
    finally:
        conn.close()


@app.post("/api/scan", dependencies=[Depends(require_scan_auth)])
def trigger_scan():
    """Trigger a full scan in the background.

    Auth: requires X-Scan-Token header in staging/production. In dev the
    check is skipped when SCAN_TOKEN is empty.
    Rate limit: 3 triggers per 60-second window (in-memory, single process).
    """
    _rate_limit_scan()
    try:
        subprocess.Popen(
            [sys.executable, "-m", "scheduler.scheduler", "--once"],
            cwd=str(REPO_ROOT / "apps" / "scanner"),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return {"status": "started"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/solvers")
def list_solvers(
    type: Optional[str] = None,
    search: Optional[str] = None,
    chain: Optional[str] = None,
    protocol: Optional[str] = None,
):
    """Return known solvers, fillers, and quoters in the intent ecosystem."""
    results = SOLVERS_DATA

    if type:
        results = [s for s in results if s["type"] == type.lower()]

    if search:
        q = search.lower()
        results = [
            s for s in results
            if q in s["name"].lower()
            or q in s["description"].lower()
            or any(q in p.lower() for p in s["protocols"])
        ]

    if chain:
        chain_lower = chain.lower()
        results = [
            s for s in results
            if any(chain_lower in c.lower() for c in s["chains"])
        ]

    if protocol:
        protocol_lower = protocol.lower()
        results = [
            s for s in results
            if any(protocol_lower in p.lower() for p in s["protocols"])
        ]

    return results


@app.get("/api/stats")
def overview_stats():
    """Return overview statistics."""
    conn = get_connection()
    try:
        projects = conn.execute("SELECT COUNT(*) as cnt FROM projects").fetchone()["cnt"]
        mentions = conn.execute("SELECT COUNT(*) as cnt FROM social_mentions").fetchone()["cnt"]
        active = conn.execute(
            "SELECT COUNT(*) as cnt FROM projects WHERE status = 'active'"
        ).fetchone()["cnt"]
        total_raised_row = conn.execute(
            "SELECT COALESCE(SUM(amount_usd), 0) as total FROM funding_rounds"
        ).fetchone()
        total_raised = total_raised_row["total"]
        unreviewed = conn.execute(
            "SELECT COUNT(*) as cnt FROM discoveries WHERE reviewed = 0"
        ).fetchone()["cnt"]

        return {
            "projects": projects,
            "mentions": mentions,
            "active": active,
            "total_raised": total_raised,
            "unreviewed": unreviewed,
        }
    finally:
        conn.close()
