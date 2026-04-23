"""Backfill role + intent_type for existing projects.

Reads every row from ``projects``, maps the legacy ``category`` via
``packages.core.taxonomy.classify`` and writes the new columns.

Requires the migration in ``supabase/migrations/001_taxonomy.sql`` to have
been applied first. Uses SUPABASE_SERVICE_KEY so it can bypass RLS.

Usage:
    python3 scripts/backfill_taxonomy.py            # live update
    python3 scripts/backfill_taxonomy.py --dry-run  # preview only
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys
from collections import Counter
from urllib.request import Request, urlopen
from urllib.error import HTTPError


def _load_env() -> dict[str, str]:
    env_path = pathlib.Path(__file__).resolve().parents[1] / ".env"
    env: dict[str, str] = {}
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip().strip('"').strip("'")
    env.update(os.environ)
    return env


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    # Import taxonomy directly by file to avoid triggering the core package's
    # __init__ (which imports pydantic_settings — not needed for a one-off script).
    import importlib.util
    tx_path = pathlib.Path(__file__).resolve().parents[1] / "packages" / "core" / "taxonomy.py"
    spec = importlib.util.spec_from_file_location("taxonomy", tx_path)
    taxonomy = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(taxonomy)
    classify = taxonomy.classify

    env = _load_env()
    url = env.get("SUPABASE_URL")
    key = env.get("SUPABASE_SERVICE_KEY") or env.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        print("ERROR: SUPABASE_URL and SUPABASE_SERVICE_KEY required")
        return 1

    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }

    # Try with role/intent_type first; fall back to pre-migration shape.
    try:
        req = Request(f"{url}/rest/v1/projects?select=id,name,category,role,intent_type", headers=headers)
        rows = json.loads(urlopen(req).read())
    except HTTPError as e:
        if e.code == 400:
            print("NOTE: role/intent_type columns not found — migration 001 not applied yet.")
            print("      Apply supabase/migrations/001_taxonomy.sql in the Supabase SQL editor, then re-run.")
            return 2
        raise
    print(f"Fetched {len(rows)} projects")

    # Classify
    plan: list[tuple[int, str, str, str, str]] = []
    counts: Counter[tuple[str, str]] = Counter()
    skipped = 0
    for r in rows:
        role, intent = classify(r.get("category"))
        counts[(role, intent)] += 1
        if r.get("role") == role and r.get("intent_type") == intent:
            skipped += 1
            continue
        plan.append((r["id"], r["name"], r.get("category") or "(null)", role, intent))

    print()
    print("=== target distribution (role/intent_type) ===")
    for (role, intent), n in counts.most_common():
        print(f"  {n:3d}  {role}/{intent}")

    print()
    print(f"=== {len(plan)} rows to update ({skipped} already correct) ===")
    for pid, name, old, role, intent in plan[:15]:
        print(f"  id={pid:3d}  {name:30s}  {old!r} -> ({role}, {intent})")
    if len(plan) > 15:
        print(f"  ... and {len(plan) - 15} more")

    if args.dry_run:
        print("\n(dry run — no changes written)")
        return 0

    print()
    print("Writing updates...")
    ok, err = 0, 0
    for pid, name, _, role, intent in plan:
        body = json.dumps({"role": role, "intent_type": intent}).encode()
        req = Request(
            f"{url}/rest/v1/projects?id=eq.{pid}",
            data=body,
            headers={**headers, "Prefer": "return=minimal"},
            method="PATCH",
        )
        try:
            urlopen(req).read()
            ok += 1
        except HTTPError as e:
            err += 1
            print(f"  FAIL id={pid} {name}: {e.code} {e.read().decode()[:100]}")
    print(f"Done. {ok} updated, {err} failed.")
    return 0 if err == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
