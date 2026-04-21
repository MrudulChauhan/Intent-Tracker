"""Export the live SQLite DB into a single JSON snapshot bundled with the web app.

Output: apps/web/src/data/snapshot.json

The web client imports this file directly, so the Next.js build is fully
self-contained — no backend required on Vercel.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

from core.db import get_connection
from core.paths import APPS_DIR


OUT = APPS_DIR / "web" / "src" / "data" / "snapshot.json"


def rows(cur) -> list[dict]:
    return [dict(r) for r in cur.fetchall()]


def main() -> None:
    conn = get_connection()

    projects = rows(conn.execute("SELECT * FROM projects ORDER BY relevance_score DESC, name"))
    mentions = rows(
        conn.execute(
            "SELECT * FROM social_mentions ORDER BY discovered_at DESC LIMIT 500"
        )
    )
    github = rows(
        conn.execute("SELECT * FROM github_metrics ORDER BY snapshot_date DESC, stars DESC")
    )
    protocol_metrics = rows(
        conn.execute(
            "SELECT * FROM protocol_metrics ORDER BY snapshot_date DESC, tvl_usd DESC"
        )
    )
    discoveries_sql = """
        SELECT
            d.id, d.entity_type, d.entity_id, d.discovered_at, d.reviewed,
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
        LEFT JOIN social_mentions sm
            ON d.entity_type = 'social_mention' AND d.entity_id = sm.id
        LEFT JOIN funding_rounds fr
            ON d.entity_type = 'funding_round' AND d.entity_id = fr.id
        LEFT JOIN projects fr_p ON fr.project_id = fr_p.id
        ORDER BY d.discovered_at DESC
        LIMIT 500
    """
    discoveries = rows(conn.execute(discoveries_sql))
    scan_log = rows(conn.execute("SELECT * FROM scan_log ORDER BY started_at DESC LIMIT 50"))

    # Mention aggregates for /api/mentions/stats
    total = conn.execute("SELECT COUNT(*) c FROM social_mentions").fetchone()["c"]
    by_source = {
        r["source"]: r["c"]
        for r in conn.execute(
            "SELECT source, COUNT(*) c FROM social_mentions GROUP BY source"
        ).fetchall()
    }

    # Overview /api/stats counterpart
    stats = {
        "projects": conn.execute("SELECT COUNT(*) c FROM projects").fetchone()["c"],
        "mentions": total,
        "active": conn.execute(
            "SELECT COUNT(*) c FROM projects WHERE status = 'active'"
        ).fetchone()["c"],
        "total_raised": conn.execute(
            "SELECT COALESCE(SUM(amount_usd), 0) t FROM funding_rounds"
        ).fetchone()["t"],
        "unreviewed": conn.execute(
            "SELECT COUNT(*) c FROM discoveries WHERE reviewed = 0"
        ).fetchone()["c"],
    }

    conn.close()

    snapshot = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "stats": stats,
        "projects": projects,
        "mentions": mentions,
        "github_metrics": github,
        "protocol_metrics": protocol_metrics,
        "discoveries": discoveries,
        "scan_log": scan_log,
        "mention_stats": {"total": total, "by_source": by_source, "this_week": 0},
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(snapshot, indent=2, default=str))

    size_kb = OUT.stat().st_size / 1024
    print(f"✓ wrote {OUT.relative_to(OUT.parents[4])}")
    print(f"  generated_at: {snapshot['generated_at']}")
    print(f"  size: {size_kb:.1f} KB")
    print(f"  projects: {len(projects)}  mentions: {len(mentions)}  "
          f"github: {len(github)}  metrics: {len(protocol_metrics)}  "
          f"discoveries: {len(discoveries)}")


if __name__ == "__main__":
    sys.exit(main())
