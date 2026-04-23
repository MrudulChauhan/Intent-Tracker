"""Seed X/Twitter accounts for the P1.4 Twitter scanner.

This list is the curated set of handles the scanner pulls tweets from daily.
Keep it tight: ~50 accounts max. More accounts => more tweets => more
rate-limit risk on the unofficial twikit API => higher ban risk on the
throwaway X account.

Rotation policy
---------------
A "useful" seed is a handle that posts about intent DeFi, solver networks,
order-flow auctions, chain abstraction, MEV, or cross-chain settlement
**at least monthly**. Accounts that go silent for 60+ days or pivot away
from intent-DeFi topics should be removed.

How to add a seed
-----------------
1. Verify the account has posted 3+ intent-DeFi-relevant tweets in the last
   60 days (check manually before adding).
2. Place it in the most-specific category dict key below (protocols /
   solvers / research / orderflow / bridges). If it fits multiple, pick
   the one that best describes the poster's primary beat.
3. Run ``scripts/test_twitter_scanner.py`` to sanity-check the list shape.
4. Commit with a one-line rationale in the commit message.

How to remove a seed
--------------------
1. Check the last_scanned_at timestamps in ``social_mentions`` -- if the
   account has produced zero kept mentions in 60+ days, drop it.
2. Accounts that get rate-limited repeatedly (protected, suspended,
   private) should also be pruned.

No leading ``@`` -- store bare handles. Case-sensitive is fine; twikit
does case-insensitive lookups.
"""

from __future__ import annotations


SEED_ACCOUNTS: dict[str, list[str]] = {
    # Protocols and solver/settlement teams that publish intent-DeFi product
    # updates, RFCs, auction designs, and post-mortems.
    "protocols": [
        "CoWSwap",
        "1inch",
        "Uniswap",
        "UniswapFND",
        "AcrossProtocol",
        "lifiprotocol",
        "SocketProtocol",
        "squidrouter",
        "hashflow",
        "bebop_dex",
        "dexhashflow",
        "KhalaniNetwork",
        "AnomaFoundation",
        "flashbots",
        "SUAVEchain",
        "RouteProcessor",
    ],
    # Solvers, market makers, liquidity providers that participate as
    # fillers/solvers in intent protocols.
    "solvers": [
        "wintermute_t",
        "0xCrypto_Jay",   # barter
        "gauntlet_xyz",
        "odos_xyz",
        "ParaSwap",
    ],
    # Researchers, economists, and protocol designers whose threads shape
    # the intent-DeFi discourse.
    "research": [
        "hasu",
        "dberenzon",
        "0xjim",
        "samczsun",
        "AndreCronjeTech",
        "EvgenyGaevoy",   # Wintermute CEO
        "bkiepuszewski",
        "thogard785",
        "PartialIntents",
        "essential_xyz",
        "BrinkTrade",
        "skip_protocol",
    ],
    # Order-flow, MEV infra, private mempools, MEV-protection RPCs.
    "orderflow": [
        "MEVBlocker",
        "rook_protocol",
        "cow_swap",
        "matchaxyz",
        "0xProject",
    ],
    # Cross-chain aggregators and bridges whose products route intents.
    "bridges": [
        "jumper_exchange",
        "rango_exchange",
        "XY_finance",
        "deBridgeFinance",
        "chainflip",
    ],
}


def get_all_seeds() -> list[str]:
    """Flatten SEED_ACCOUNTS into a single de-duplicated handle list.

    Order is preserved by category then insertion order -- stable ordering
    makes scan logs easier to diff week over week.
    """
    seen: set[str] = set()
    flat: list[str] = []
    for _category, handles in SEED_ACCOUNTS.items():
        for handle in handles:
            normalized = handle.lstrip("@").strip()
            if not normalized:
                continue
            key = normalized.lower()
            if key in seen:
                continue
            seen.add(key)
            flat.append(normalized)
    return flat


def get_category_for(handle: str) -> str | None:
    """Return the category bucket for a given handle, or None if unknown."""
    target = handle.lstrip("@").strip().lower()
    for category, handles in SEED_ACCOUNTS.items():
        for h in handles:
            if h.lstrip("@").strip().lower() == target:
                return category
    return None
