#!/usr/bin/env python3
"""Dry-run the narratives prompt with a fake mention set.

Prints:
  - the system prompt (stable across runs — cached by Anthropic on the wire)
  - the rendered user prompt built from a small synthetic mention list
  - a few derived stats

Does NOT call the Anthropic API or touch Supabase. Safe to run with no env
vars set. Useful when tweaking NARRATIVES_SYSTEM_PROMPT or the mention
rendering logic.

Run:
    uv run python scripts/test_narratives_prompt.py
"""

from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path


# Make `processing.narratives` importable without running the scanner app.
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "apps" / "scanner"))
sys.path.insert(0, str(REPO_ROOT / "packages"))


from processing.narratives import (  # noqa: E402
    MAX_SNIPPET_CHARS,
    NARRATIVES_MODEL,
    NARRATIVES_SYSTEM_PROMPT,
    render_mentions_prompt,
)


FAKE_MENTIONS: list[dict] = [
    {
        "id": 101,
        "source": "reddit",
        "title": "UniswapX solvers now settling cross-chain swaps on Arbitrum",
        "content_snippet": (
            "UniswapX's solver network rolled out Arbitrum settlement this "
            "week; early volume suggests meaningful orderflow migrating from "
            "1inch Fusion. Filler competition is tight."
        ),
    },
    {
        "id": 102,
        "source": "rss",
        "title": "CoW Protocol launches batch auction v2 with MEV rebate",
        "content_snippet": (
            "CoW Protocol's v2 batch auction promises MEV rebates to users, "
            "paid out of surplus. Analysts compare design to Flashbots SUAVE."
        ),
    },
    {
        "id": 103,
        "source": "google_news",
        "title": "Across Bridge TVL crosses $500M amid intents hype",
        "content_snippet": (
            "Across Bridge hit a new TVL high as chain abstraction narratives "
            "drove deposits. deBridge and Hop also saw inflows."
        ),
    },
    {
        "id": 104,
        "source": "reddit",
        "title": "Why are solvers suddenly everyone's favorite infra bet?",
        "content_snippet": (
            "A thread arguing solvers are the new L2s — undervalued picks-"
            "and-shovels play on intent-based DeFi. Discussion around "
            "1inch Fusion, UniswapX, CoW Protocol throughout."
        ),
    },
    {
        "id": 105,
        "source": "blogs",
        "title": "SUAVE's first mainnet solvers go live",
        "content_snippet": (
            "Flashbots SUAVE now has active solvers routing orderflow. The "
            "MEV redistribution story is starting to feel real."
        ),
    },
    {
        "id": 106,
        "source": "google_news",
        "title": "deBridge announces gasless cross-chain swaps",
        "content_snippet": (
            "deBridge's new gasless flow wraps a meta-transaction solver "
            "pattern; competes directly with Across's intent-based bridge."
        ),
    },
]


def main() -> int:
    week_start = date.today() - timedelta(days=date.today().weekday())

    print("=" * 72)
    print(f"MODEL: {NARRATIVES_MODEL}")
    print(f"WEEK_START: {week_start.isoformat()}")
    print(f"MAX_SNIPPET_CHARS: {MAX_SNIPPET_CHARS}")
    print("=" * 72)
    print("\n--- SYSTEM PROMPT (cached) ---\n")
    print(NARRATIVES_SYSTEM_PROMPT)

    user_prompt = render_mentions_prompt(FAKE_MENTIONS, week_start)
    print("\n--- USER PROMPT ---\n")
    print(user_prompt)
    print("\n--- STATS ---")
    print(f"system prompt chars: {len(NARRATIVES_SYSTEM_PROMPT)}")
    print(f"user prompt chars:   {len(user_prompt)}")
    print(f"mention count:       {len(FAKE_MENTIONS)}")
    print("\nNo API call was made.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
