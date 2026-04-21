"""One-shot migration: local SQLite → Supabase Postgres.

Reads data/intent_tracker.db and bulk-inserts into the Supabase project
identified by SUPABASE_URL / SUPABASE_SERVICE_KEY.

Preserves referential integrity:
  projects → funding_rounds, github_metrics, protocol_metrics, social_mentions
  ↳ discoveries (which reference projects / mentions / funding_rounds by id)

Because the SQLite `id` columns become different Postgres `id` values after
insert, we maintain an {old_id: new_id} map per table and remap foreign keys
before sending downstream rows.
"""

from __future__ import annotations

import json
import sys
import time
from typing import Any

import httpx

from core.config import settings
from core.db import get_connection


def _json_safe(row: dict[str, Any]) -> dict[str, Any]:
    """Normalize values for PostgREST — parse JSON strings to native, skip id."""
    out = {}
    for k, v in row.items():
        if k == "id":
            continue  # let Postgres assign
        if k in ("chains", "investors") and isinstance(v, str) and v:
            try:
                out[k] = json.loads(v)
                continue
            except (json.JSONDecodeError, TypeError):
                out[k] = None
                continue
        out[k] = v
    return out


def main() -> int:
    url = settings.supabase_url
    key = settings.supabase_service_key
    if not url or not key:
        print("ERROR: SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in .env")
        return 1

    base = url.rstrip("/") + "/rest/v1"
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }
    client = httpx.Client(timeout=60.0, headers=headers)

    def post_batch(table: str, rows: list[dict], on_conflict: str | None = None,
                   ignore_duplicates: bool = False) -> list[dict]:
        if not rows:
            return []
        url = f"{base}/{table}"
        params = {}
        h = dict(headers)
        if on_conflict:
            params["on_conflict"] = on_conflict
            h["Prefer"] = (
                "return=representation,resolution=ignore-duplicates"
                if ignore_duplicates
                else "return=representation,resolution=merge-duplicates"
            )
        resp = client.post(url, params=params, headers=h, json=rows)
        if resp.status_code >= 400:
            print(f"  ⚠ {table} batch failed ({resp.status_code}): {resp.text[:300]}")
            return []
        return resp.json()

    conn = get_connection()
    conn.row_factory = lambda cur, row: {
        col[0]: row[i] for i, col in enumerate(cur.description)
    }

    # ---- projects ---------------------------------------------------------
    print("→ projects")
    rows = conn.execute(
        "SELECT * FROM projects ORDER BY id"
    ).fetchall()
    project_map: dict[int, int] = {}
    inserted = 0
    for i in range(0, len(rows), 100):
        batch = rows[i : i + 100]
        payload = [_json_safe(r) for r in batch]
        out = post_batch("projects", payload, on_conflict="name")
        # PostgREST returns rows in same order as input
        for src, dst in zip(batch, out):
            if "id" in dst:
                project_map[src["id"]] = dst["id"]
        inserted += len(out)
    print(f"  ✓ {inserted} projects inserted/upserted")

    # ---- funding_rounds ---------------------------------------------------
    print("→ funding_rounds")
    rows = conn.execute("SELECT * FROM funding_rounds ORDER BY id").fetchall()
    inserted = 0
    for i in range(0, len(rows), 100):
        batch = rows[i : i + 100]
        payload = []
        for r in batch:
            r = _json_safe(r)
            if r.get("project_id") is not None:
                r["project_id"] = project_map.get(r["project_id"])
            payload.append(r)
        out = post_batch("funding_rounds", payload)
        inserted += len(out)
    print(f"  ✓ {inserted} funding_rounds")

    # ---- people -----------------------------------------------------------
    print("→ people")
    rows = conn.execute("SELECT * FROM people ORDER BY id").fetchall()
    inserted = 0
    for i in range(0, len(rows), 100):
        batch = rows[i : i + 100]
        payload = []
        for r in batch:
            r = _json_safe(r)
            if r.get("project_id") is not None:
                r["project_id"] = project_map.get(r["project_id"])
            payload.append(r)
        out = post_batch("people", payload)
        inserted += len(out)
    print(f"  ✓ {inserted} people")

    # ---- social_mentions --------------------------------------------------
    print("→ social_mentions")
    rows = conn.execute("SELECT * FROM social_mentions ORDER BY id").fetchall()
    mention_map: dict[int, int] = {}
    inserted = 0
    for i in range(0, len(rows), 200):
        batch = rows[i : i + 200]
        payload = []
        for r in batch:
            r2 = _json_safe(r)
            if r2.get("project_id") is not None:
                r2["project_id"] = project_map.get(r2["project_id"])
            payload.append(r2)
        out = post_batch("social_mentions", payload, on_conflict="url",
                         ignore_duplicates=True)
        for src, dst in zip(batch, out):
            if "id" in dst:
                mention_map[src["id"]] = dst["id"]
        inserted += len(out)
        time.sleep(0.05)  # gentle pacing
    print(f"  ✓ {inserted} social_mentions")

    # ---- github_metrics ---------------------------------------------------
    print("→ github_metrics")
    rows = conn.execute("SELECT * FROM github_metrics ORDER BY id").fetchall()
    inserted = 0
    for i in range(0, len(rows), 100):
        batch = rows[i : i + 100]
        payload = []
        for r in batch:
            r = _json_safe(r)
            if r.get("project_id") is not None:
                r["project_id"] = project_map.get(r["project_id"])
            payload.append(r)
        out = post_batch("github_metrics", payload)
        inserted += len(out)
    print(f"  ✓ {inserted} github_metrics")

    # ---- protocol_metrics -------------------------------------------------
    print("→ protocol_metrics")
    rows = conn.execute("SELECT * FROM protocol_metrics ORDER BY id").fetchall()
    inserted = 0
    for i in range(0, len(rows), 200):
        batch = rows[i : i + 200]
        payload = []
        for r in batch:
            r = _json_safe(r)
            if r.get("project_id") is not None:
                r["project_id"] = project_map.get(r["project_id"])
            payload.append(r)
        out = post_batch("protocol_metrics", payload)
        inserted += len(out)
    print(f"  ✓ {inserted} protocol_metrics")

    # ---- scan_log ---------------------------------------------------------
    print("→ scan_log")
    rows = conn.execute("SELECT * FROM scan_log ORDER BY id").fetchall()
    inserted = 0
    for i in range(0, len(rows), 100):
        batch = rows[i : i + 100]
        payload = [_json_safe(r) for r in batch]
        out = post_batch("scan_log", payload)
        inserted += len(out)
    print(f"  ✓ {inserted} scan_log")

    # ---- discoveries ------------------------------------------------------
    # entity_id references projects / social_mentions / funding_rounds — remap.
    # funding_rounds don't keep an old→new map so discoveries of type
    # 'funding_round' will be skipped (scanner re-discovers them on next scan).
    print("→ discoveries")
    rows = conn.execute("SELECT * FROM discoveries ORDER BY id").fetchall()
    inserted = 0
    skipped = 0
    for i in range(0, len(rows), 200):
        batch = rows[i : i + 200]
        payload = []
        for r in batch:
            r = _json_safe(r)
            old_id = r.get("entity_id")
            t = r.get("entity_type")
            new_id = None
            if t == "project":
                new_id = project_map.get(old_id)
            elif t == "social_mention":
                new_id = mention_map.get(old_id)
            if new_id is None:
                skipped += 1
                continue
            r["entity_id"] = new_id
            payload.append(r)
        out = post_batch("discoveries", payload)
        inserted += len(out)
    print(f"  ✓ {inserted} discoveries ({skipped} skipped — unmappable entity_id)")

    conn.close()
    client.close()
    print("\n✓ migration complete")
    return 0


if __name__ == "__main__":
    sys.exit(main())
