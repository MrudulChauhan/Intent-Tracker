#!/usr/bin/env python3
"""Dry-run validator for the OnchainDuneScanner (P1.5).

Imports the scanner, sanity-checks DUNE_QUERIES, and prints a summary table.
Does NOT make any network calls and does NOT require DUNE_API_KEY or any
Supabase credentials — safe to run in CI / on a freshly-cloned worktree.

Usage:
    python scripts/test_onchain_dune.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Ensure apps/scanner is importable the same way scripts/run_scan.sh sets it up.
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "apps" / "scanner"))
sys.path.insert(0, str(REPO_ROOT / "packages"))


def main() -> int:
    # Import lives inside main() so a broken import surfaces with a clear exit.
    try:
        from scanners.onchain_dune import (  # type: ignore
            DUNE_QUERIES,
            OnchainDuneScanner,
            _EXPECTED_COLUMN_ALIASES,
        )
    except ImportError as exc:
        print(f"[FAIL] Could not import OnchainDuneScanner: {exc}")
        return 1

    print("=" * 72)
    print(" OnchainDuneScanner — dry-run config check")
    print("=" * 72)

    scanner = OnchainDuneScanner(writer=None)
    assert scanner.name == "onchain_dune", "scanner.name must be 'onchain_dune'"
    print(f"name           : {scanner.name}")
    print(f"writer         : {scanner._writer!r} (expected None in dry-run)")
    print(f"DUNE_API_KEY   : {'set' if os.environ.get('DUNE_API_KEY') else 'unset (dry-run)'}")
    print()

    if not isinstance(DUNE_QUERIES, dict) or not DUNE_QUERIES:
        print("[FAIL] DUNE_QUERIES must be a non-empty dict")
        return 1

    print(f"{'protocol':<18} {'query_id':<12} {'chain':<12} status")
    print("-" * 60)
    configured = 0
    for proto, cfg in DUNE_QUERIES.items():
        qid = cfg.get("query_id")
        chain = cfg.get("chain", "?")
        status = "configured" if qid is not None else "TODO"
        if qid is not None:
            configured += 1
        print(f"{proto:<18} {str(qid):<12} {chain:<12} {status}")

    print()
    print(f"Protocols configured : {configured} / {len(DUNE_QUERIES)}")
    print(f"Expected columns     : {', '.join(_EXPECTED_COLUMN_ALIASES.keys())}")
    print()

    # Exercise _normalise_row with a fake row to make sure the alias map works
    # without touching the network.
    sample = {
        "block_time": "2026-04-20 12:34:56.000 UTC",
        "tx_hash": "0xABCDEF",
        "solver": "0xDEADBEEF",
        "amount_in_usd": "1234.5",
        "token_in": "USDC",
        "token_out": "WETH",
        "user": "0xCAFE",
    }
    normalised = OnchainDuneScanner._normalise_row("cow_protocol", "ethereum", sample)
    if not normalised:
        print("[FAIL] _normalise_row returned None for a valid sample row")
        return 1

    required = {"protocol", "tx_hash", "solver_address", "amount_in_usd",
                "block_time", "chain", "token_in", "token_out",
                "user_address", "raw_event"}
    missing = required - set(normalised.keys())
    if missing:
        print(f"[FAIL] Normalised row missing keys: {missing}")
        return 1
    if normalised["tx_hash"] != "0xabcdef":
        print("[FAIL] tx_hash should be lowercased")
        return 1
    if not isinstance(normalised["amount_in_usd"], float):
        print("[FAIL] amount_in_usd should coerce to float")
        return 1

    print("Sample row normalisation : OK")
    print("No live API calls made   : OK")
    print()
    print("[PASS] OnchainDuneScanner dry-run checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
