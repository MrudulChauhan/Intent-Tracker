#!/usr/bin/env python3
"""Dry-run verifier for the P1.4 Twitter scanner.

Does NOT log into X and does NOT call the network. Purely a config /
import sanity check:

1. Loads ``config.twitter_seeds`` and prints the seed list (grouped +
   flat count).
2. Imports ``scanners.twitter.TwitterScanner`` to catch syntax / import
   errors.
3. Reports which auth mode (cookies vs password) the current environment
   would use -- without performing the auth.

Run::

    uv run python scripts/test_twitter_scanner.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


def _ensure_path() -> None:
    """Add apps/scanner and packages/core to sys.path so this script works
    the same way the scheduler does (see scripts/_env.sh)."""
    repo_root = Path(__file__).resolve().parent.parent
    for sub in ("apps/scanner", "packages", "."):
        p = str(repo_root / sub)
        if p not in sys.path:
            sys.path.insert(0, p)


def _report_auth_mode() -> str:
    cookies = (os.getenv("X_COOKIES_FILE") or "").strip()
    user = (os.getenv("X_USERNAME") or "").strip()
    email = (os.getenv("X_EMAIL") or "").strip()
    pw = (os.getenv("X_PASSWORD") or "").strip()

    if cookies and Path(cookies).expanduser().is_file():
        return f"cookies ({cookies})"
    if cookies:
        return f"cookies MISSING file {cookies}; would fall back to password"
    if user and email and pw:
        return f"password (username={user})"
    return "NONE -- scanner would raise ValueError at scan() time"


def main() -> int:
    _ensure_path()

    # 1. Seed list
    from config.twitter_seeds import SEED_ACCOUNTS, get_all_seeds

    seeds = get_all_seeds()
    print("=" * 60)
    print("Seed accounts by category:")
    for cat, handles in SEED_ACCOUNTS.items():
        print(f"  [{cat}] ({len(handles)}): {', '.join(handles)}")
    print(f"\nFlat unique seeds: {len(seeds)}")
    print("=" * 60)

    # 2. Import scanner
    try:
        from scanners.twitter import TwitterScanner
    except Exception as e:  # noqa: BLE001
        print(f"IMPORT FAILED: {e}", file=sys.stderr)
        return 1

    scanner = TwitterScanner()
    print(f"Scanner instantiated: name={scanner.name!r}")
    print(f"  relevance_threshold = {scanner.relevance_threshold}")
    print(f"  tweets_per_seed     = {scanner.tweets_per_seed}")
    print(f"  seconds_between_seeds = {scanner.seconds_between_seeds}")

    # 3. Auth mode
    print(f"  auth mode (dry-run): {_report_auth_mode()}")

    # 4. What scan() would do (describe, don't execute)
    print(
        f"\nscan() would: hit {len(seeds)} handles, "
        f"request {scanner.tweets_per_seed} tweets each "
        f"(~{len(seeds) * scanner.tweets_per_seed} tweets max), "
        "then filter by relevance score, dedup by normalized URL, and emit "
        "mention dicts with source='twitter'."
    )
    print("Dry-run OK. No network calls were made.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
