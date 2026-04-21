"""
Keyword lists and taxonomy for intent-based DeFi ecosystem tracking.
"""

# High-signal terms — a match on any of these alone is relevant
PRIMARY_TERMS = [
    "intent-based",
    "intent solver",
    "intent settlement",
    "intent architecture",
    "intent transaction",
    "intent protocol",
    "intent network",
    "intent layer",
    "intent order",
    "solver network",
    "solver auction",
    "solver competition",
    "order flow auction",
    "batch auction",
    "chain abstraction",
    "RFQ",
    "request for quote",
    "filler",
    "order filler",
    "quoter",
    "quote provider",
    "gasless swap",
    "meta-transaction",
]

# DeFi qualifiers — must co-occur with generic terms to confirm relevance
CONTEXT_TERMS = [
    "defi",
    "protocol",
    "blockchain",
    "on-chain",
    "cross-chain",
    "solver",
    "settlement",
    "order flow",
    "dex",
    "swap",
    "liquidity",
    "mev",
    "gasless",
]

# Specific protocol names — unique enough to match standalone
# These will ALWAYS be treated as relevant when found
# Include common variations (with/without spaces, abbreviations)
PROTOCOL_NAMES_EXACT = [
    "UniswapX",
    "CoW Protocol",
    "CoW Swap",
    "CoWSwap",
    "CowSwap",
    "1inch Fusion",
    "Across Protocol",
    "Across Bridge",
    "Anoma",
    "Namada",
    "SUAVE",
    "Khalani",
    "Brink Trade",
    "Enso Finance",
    "PropellerHeads",
    "MEV Blocker",
    "Squid Router",
    "LI.FI",
    "Aori",
    "SYMMIO",
    "Mantis",
    "Safe Global",
    "Safe Wallet",
    # Solvers / Fillers / Quoters
    "Wintermute",
    "Tokka Labs",
    "Bebop",
    "Hashflow",
    "Airswap",
    "AirSwap",
    "0x Protocol",
    "Matcha",
    "Paraswap",
    "ParaSwap",
    "Flood Protocol",
    "Atlas FastLane",
    "FastLane Labs",
    "Odos",
    # Intent-driven systems
    "Everclear",
    "Connext",
    "Hop Protocol",
    "Stargate",
    "LayerZero",
    "Wormhole",
    "Penumbra",
    "Skip Protocol",
    "Router Protocol",
    "Garden Finance",
    "Catalyst",
    "Bungee",
    # Additional
    "Near Intents",
    "Jupiter",
    "JupiterZ",
    "dYdX",
    "Osmosis",
]

# Generic protocol names — these need additional context (must co-occur with
# PRIMARY_TERMS or CONTEXT_TERMS related to intents) to avoid false positives.
# e.g. "Safe" alone matches Safe staking, Safe CEX, etc.
PROTOCOL_NAMES_CONTEXTUAL = [
    "Flashbots",
    "deBridge",
    "DLN",
    "Socket",
    "Particle Network",
    "Biconomy",
    "ZeroDev",
    "Essential",
]

# Combined list for backwards compatibility
PROTOCOL_NAMES = PROTOCOL_NAMES_EXACT + PROTOCOL_NAMES_CONTEXTUAL

# Category taxonomy for classifying signals
CATEGORIES = {
    "solver_infra": "Solver infrastructure, auction mechanisms, and competition dynamics",
    "cross_chain": "Cross-chain intent settlement and bridging",
    "order_flow": "Order-flow routing, aggregation, and MEV protection",
    "account_abstraction": "Account abstraction and smart-account intent layers",
    "protocol_update": "Protocol upgrades, governance proposals, and roadmap changes",
    "tvl_volume": "TVL movements, volume metrics, and on-chain activity",
    "funding_partnership": "Funding rounds, partnerships, and ecosystem grants",
    "research": "Academic papers, blog posts, and technical deep-dives",
    "community": "Community sentiment, governance discussions, and social signals",
}

# Chains where intent protocols are deployed or relevant
TRACKED_CHAINS = [
    "Ethereum",
    "Arbitrum",
    "Optimism",
    "Base",
    "Polygon",
    "BNB Chain",
    "Avalanche",
    "Gnosis Chain",
    "Fantom",
    "zkSync Era",
    "Linea",
    "Scroll",
    "Mantle",
    "Blast",
    "Mode",
    "Solana",
    "Cosmos",
    "Osmosis",
    "Celestia",
    "Sei",
]
