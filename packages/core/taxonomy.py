"""Canonical two-level taxonomy for intent-based DeFi projects.

Every project has a (role, intent_type) pair. Scanners and seeds route through
``classify()`` so we don't accumulate drift like "Dexs" vs "DEX" vs "dex".
"""

from __future__ import annotations

from typing import Optional

# ---- Canonical values ------------------------------------------------------

ROLES: tuple[str, ...] = (
    "solver",        # entity that fills intents (UniswapX solver, CoW solver)
    "protocol",      # intent-based protocol (CoW Protocol, Across, Uniswap)
    "aggregator",    # aggregates other protocols (1inch, Matcha, LiFi)
    "infra",         # infrastructure (Khalani, Anoma, Flashbots, Reservoir)
    "interface",     # wallet, frontend, bot (Safe UI, MetaMask, TG bots)
    "tool",          # analytics, calculator, DCA, utility
)

INTENT_TYPES: tuple[str, ...] = (
    "swap",                  # spot swaps
    "bridge",                # cross-chain transfers
    "derivatives",           # perps, options, futures, basis, synthetics
    "lending",               # lending / borrowing
    "yield",                 # yield seeking / aggregation
    "liquid_staking",        # LST protocols
    "orderflow_auction",     # OFA / batch auctions / order flow
    "account_abstraction",   # ERC-4337, smart accounts
    "mev",                   # MEV-specific infra
    "privacy",               # privacy-preserving intents
    "launchpad",             # token launches with intent layer
    "general",               # broad / multi-type / utility
)

# ---- Mapping: legacy category value -> (role, intent_type) -----------------
# Keys are lower-cased + whitespace-stripped on lookup.

_LEGACY_MAP: dict[str, tuple[str, str]] = {
    "solver_infra":         ("infra", "swap"),
    "dexs":                 ("protocol", "swap"),
    "dex":                  ("protocol", "swap"),
    "dex aggregator":       ("aggregator", "swap"),
    "derivatives":          ("protocol", "derivatives"),
    "cross chain bridge":   ("protocol", "bridge"),
    "bridge":               ("protocol", "bridge"),
    "cross_chain":          ("protocol", "bridge"),
    "lending":              ("protocol", "lending"),
    "interface":            ("interface", "general"),
    "bridge aggregator":    ("aggregator", "bridge"),
    "order_flow":           ("protocol", "orderflow_auction"),
    "yield":                ("protocol", "yield"),
    "launchpad":            ("protocol", "launchpad"),
    "liquid staking":       ("protocol", "liquid_staking"),
    "privacy":              ("protocol", "privacy"),
    "mev":                  ("infra", "mev"),
    "services":             ("tool", "general"),
    "basis trading":        ("protocol", "derivatives"),
    "chain":                ("infra", "general"),
    "synthetics":           ("protocol", "derivatives"),
    "telegram bot":         ("interface", "general"),
    "dca tools":            ("tool", "swap"),
    "trading app":          ("interface", "swap"),
    "reserve currency":     ("protocol", "general"),
    "account_abstraction":  ("infra", "account_abstraction"),
}


def classify(category: Optional[str]) -> tuple[str, str]:
    """Map a legacy ``category`` string to ``(role, intent_type)``.

    Unknown or null categories default to ``("protocol", "general")`` so a row
    is always flaggable for manual review rather than silently dropping.
    """
    if not category:
        return ("protocol", "general")
    key = category.strip().lower()
    return _LEGACY_MAP.get(key, ("protocol", "general"))


def is_canonical(role: str, intent_type: str) -> bool:
    return role in ROLES and intent_type in INTENT_TYPES


def display_label(role: str, intent_type: str) -> str:
    """Human-readable label, e.g. ('aggregator', 'bridge') -> 'Bridge Aggregator'."""
    pretty_role = {
        "solver": "Solver",
        "protocol": "",            # 'bridge' alone reads fine; role omitted
        "aggregator": "Aggregator",
        "infra": "Infra",
        "interface": "Interface",
        "tool": "Tool",
    }.get(role, role.title())

    pretty_intent = {
        "swap": "DEX",
        "bridge": "Bridge",
        "derivatives": "Derivatives",
        "lending": "Lending",
        "yield": "Yield",
        "liquid_staking": "Liquid Staking",
        "orderflow_auction": "Order Flow",
        "account_abstraction": "Account Abstraction",
        "mev": "MEV",
        "privacy": "Privacy",
        "launchpad": "Launchpad",
        "general": "",
    }.get(intent_type, intent_type.replace("_", " ").title())

    if pretty_role and pretty_intent:
        return f"{pretty_intent} {pretty_role}".strip()
    return (pretty_intent or pretty_role or "Other").strip()
