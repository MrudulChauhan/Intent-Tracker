"""
Data-source definitions for the Intent Tracker OSINT tool.
"""

# Reddit subreddits to monitor
SUBREDDITS = [
    "ethereum",
    "defi",
    "CryptoTechnology",
    "ethfinance",
    "cosmosnetwork",
    "UniSwap",
    "MEV",
    "flashbots",
    "CowProtocol",
]

# GitHub repositories for tracked protocols (owner/repo)
GITHUB_REPOS = [
    "Uniswap/UniswapX",
    "cowprotocol/cow-sdk",
    "cowprotocol/services",
    "1inch/fusion-sdk",
    "across-protocol/contracts",
    "across-protocol/sdk",
    "anoma/anoma",
    "anoma/namada",
    "essential-contributions/essential-integration",
    "flashbots/suave-geth",
    "flashbots/mev-boost",
    "debridge-finance/debridge-contracts-v1",
    "debridge-finance/dln-contracts",
    "0xsquid/squid-sdk",
    "SocketDotTech/socket-DL",
    "lifinance/sdk",
    "particle-network/particle-network",
    "bcnmy/biconomy-client-sdk",
    "brink-trade/brink-sdk",
    "EnsoFinance/shortcuts-contracts",
    "propellerheads/propeller-protocol-lib",
    "zerodevapp/sdk",
    "safe-global/safe-smart-account",
    "connext/monorepo",
    "hop-protocol/hop-monorepo",
    "stargate-protocol/stargate-v2",
    "LayerZero-Labs/LayerZero-v2",
    "wormhole-foundation/wormhole",
    "penumbra-zone/penumbra",
    "skip-mev/skip-go-sdk",
    "router-protocol/router-contracts",
    "bebop-dex/bebop-sdk",
    "hashflow/hashflow-sdk",
    "airswap/airswap-protocols",
    "0xProject/protocol",
    "jup-ag/jupiter-core",
    "dydxprotocol/v4-chain",
    "osmosis-labs/osmosis",
    "catalystdao/catalyst",
    "floodprotocol/flood-contracts",
]

# RSS feeds for crypto news outlets
RSS_FEEDS = [
    "https://www.theblock.co/rss.xml",
    "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "https://decrypt.co/feed",
    "https://blockworks.co/feed",
    # Additional crypto news
    "https://cointelegraph.com/rss",
    "https://www.dlnews.com/arc/outboundfeeds/rss/",
]

# Reddit public RSS — no API key needed
# Format: subreddit search RSS for specific terms
_REDDIT_SEARCH_TERMS = [
    "intent-based",
    "intent+solver",
    "intent+settlement",
    "solver+network",
    "UniswapX",
    "CoW+Protocol",
    "cross-chain+intents",
    "chain+abstraction+defi",
    "Across+Protocol",
    "Anoma",
    "SUAVE+Flashbots",
    "deBridge",
    "order+flow+auction",
    "batch+auction+defi",
    "account+abstraction",
]

_REDDIT_SUBREDDITS = [
    "ethereum", "defi", "CryptoTechnology", "ethfinance",
    "cosmosnetwork", "UniSwap", "MEV", "flashbots", "CowProtocol",
    "solana", "cryptocurrency",
]

# Generate Reddit RSS feed URLs
REDDIT_RSS_FEEDS = []

# Subreddit new posts RSS (top recent posts from each subreddit)
for _sub in _REDDIT_SUBREDDITS:
    REDDIT_RSS_FEEDS.append(f"https://www.reddit.com/r/{_sub}/new/.rss?limit=50")

# Subreddit search RSS (search specific terms across key subreddits)
for _term in _REDDIT_SEARCH_TERMS:
    for _sub in ["defi", "ethereum", "CryptoTechnology"]:
        REDDIT_RSS_FEEDS.append(
            f"https://www.reddit.com/r/{_sub}/search/.rss?q={_term}&restrict_sr=on&sort=new&t=week&limit=25"
        )

# DefiLlama protocol slugs for TVL / volume queries
DEFILLAMA_PROTOCOLS = [
    "uniswap",
    "cow-protocol",
    "1inch-network",
    "across-protocol",
    "debridge",
    "squid",
    "socket",
    "lifi",
    "biconomy",
    "safe",
    "stargate",
    "layerzero",
    "hop-protocol",
    "hashflow",
    "0x-protocol",
    "paraswap",
    "jupiter",
    "dydx",
    "osmosis-dex",
    "wormhole",
    "everclear",
    "bebop",
]

# CoinGecko IDs for price and market-cap lookups
COINGECKO_IDS = {
    "CoW Protocol": "cow-protocol",
    "1inch": "1inch",
    "Across Protocol": "across-protocol",
    "Anoma": "anoma",
    "Namada": "namada",
    "Flashbots": "flashbots",
    "deBridge": "debridge",
    "Particle Network": "particle-network",
    "Biconomy": "biconomy",
    "Safe": "safe",
    "LayerZero": "layerzero",
    "Stargate": "stargate-finance",
    "Wormhole": "wormhole",
    "dYdX": "dydx-chain",
    "Osmosis": "osmosis",
    "Jupiter": "jupiter-exchange-solana",
    "Hop Protocol": "hop-protocol",
    "Hashflow": "hashflow",
    "0x Protocol": "0x-protocol",
    "Paraswap": "paraswap",
}

# Blog / Mirror / Medium URLs for each protocol
BLOG_SOURCES = {
    "UniswapX": "https://blog.uniswap.org",
    "CoW Protocol": "https://blog.cow.fi",
    "1inch Fusion": "https://blog.1inch.io",
    "Across Protocol": "https://medium.com/across-protocol",
    "Anoma": "https://anoma.net/blog",
    "Namada": "https://namada.net/blog",
    "Essential": "https://blog.essential.builders",
    "Flashbots": "https://writings.flashbots.net",
    "deBridge": "https://blog.debridge.finance",
    "Squid Router": "https://medium.com/@squidrouter",
    "Socket": "https://mirror.xyz/socketprotocol.eth",
    "LI.FI": "https://blog.li.fi",
    "Particle Network": "https://blog.particle.network",
    "Biconomy": "https://medium.com/biconomy",
    "Khalani Network": "https://mirror.xyz/khalani.eth",
    "Enso Finance": "https://mirror.xyz/ensofinance.eth",
    "PropellerHeads": "https://blog.propellerheads.xyz",
    "ZeroDev": "https://docs.zerodev.app/blog",
    "Safe": "https://safe.mirror.xyz",
}
