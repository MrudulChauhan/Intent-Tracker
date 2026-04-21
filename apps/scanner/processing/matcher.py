"""Keyword matching and relevance scoring for intent-based DeFi content."""

from config.keywords import (
    PRIMARY_TERMS,
    CONTEXT_TERMS,
    PROTOCOL_NAMES_EXACT,
    PROTOCOL_NAMES_CONTEXTUAL,
    PROTOCOL_NAMES,
)


def score_relevance(text: str) -> float:
    """Return a relevance score between 0.0 and 1.0 for the given text.

    Scoring logic:
    - Exact protocol name match (UniswapX, CoW Protocol, etc.): 0.9
    - Contextual protocol name + intent context co-occurrence: 0.7
    - Contextual protocol name alone (Flashbots, Safe, etc.): 0.15 (not enough)
    - Primary term match: 0.7
    - Primary + context term co-occurrence: 0.8
    - Context term alone: 0.1
    - Multiple matches boost the score (capped at 1.0)
    """
    if not text:
        return 0.0

    text_lower = text.lower()

    import re

    def _word_match(term, text_l):
        """Match term as a whole word/phrase, not as a substring."""
        pattern = r'(?<![a-zA-Z])' + re.escape(term.lower()) + r'(?![a-zA-Z])'
        return bool(re.search(pattern, text_l))

    exact_hits = [p for p in PROTOCOL_NAMES_EXACT if _word_match(p, text_lower)]
    contextual_hits = [p for p in PROTOCOL_NAMES_CONTEXTUAL if _word_match(p, text_lower)]
    primary_hits = [t for t in PRIMARY_TERMS if t.lower() in text_lower]
    context_hits = [t for t in CONTEXT_TERMS if t.lower() in text_lower]

    # Intent-specific context terms that qualify a contextual protocol name
    intent_context = primary_hits or any(
        term in text_lower for term in [
            "intent", "solver", "order flow", "batch auction",
            "chain abstraction", "mev", "gasless", "meta-transaction",
            "cross-chain", "settlement layer",
        ]
    )

    score = 0.0

    # Exact protocol name — always relevant
    if exact_hits:
        score = max(score, 0.9)
        score += 0.02 * (len(exact_hits) - 1)

    # Contextual protocol name + intent context — relevant
    if contextual_hits and intent_context:
        score = max(score, 0.7)
        score += 0.02 * (len(contextual_hits) - 1)

    # Contextual protocol name alone — NOT enough (likely false positive)
    elif contextual_hits and not intent_context:
        score = max(score, 0.15)

    # Primary + context co-occurrence
    if primary_hits and context_hits:
        score = max(score, 0.8)
        score += 0.02 * (len(primary_hits) + len(context_hits) - 2)

    # Primary term alone
    elif primary_hits:
        score = max(score, 0.7)
        score += 0.02 * (len(primary_hits) - 1)

    # Context term alone — low signal
    elif context_hits and score < 0.1:
        score = 0.1

    return min(score, 1.0)


def is_relevant(text: str, threshold: float = 0.3) -> bool:
    """Return True if the text meets the relevance threshold."""
    return score_relevance(text) >= threshold


def extract_matches(text: str) -> dict:
    """Extract matched keywords from text."""
    if not text:
        return {"protocols": [], "primary_terms": [], "context_terms": []}

    text_lower = text.lower()

    import re

    def _word_match(term, text_l):
        pattern = r'(?<![a-zA-Z])' + re.escape(term.lower()) + r'(?![a-zA-Z])'
        return bool(re.search(pattern, text_l))

    return {
        "protocols": [p for p in PROTOCOL_NAMES if _word_match(p, text_lower)],
        "primary_terms": [t for t in PRIMARY_TERMS if t.lower() in text_lower],
        "context_terms": [t for t in CONTEXT_TERMS if t.lower() in text_lower],
    }


def categorize_project(text: str) -> str:
    """Guess a project category based on content keywords."""
    if not text:
        return "other"

    text_lower = text.lower()

    categories = {
        "solver": ["solver", "solving", "filler", "order filler", "solution provider"],
        "orderflow": [
            "order flow", "orderflow", "order routing", "ofa",
            "mev protection", "private orderflow",
        ],
        "dex": [
            "dex", "decentralized exchange", "swap", "amm",
            "liquidity pool", "trading pair",
        ],
        "bridge": [
            "bridge", "cross-chain", "crosschain", "interoperability",
            "chain abstraction", "multichain",
        ],
        "aggregator": [
            "aggregator", "meta-aggregator", "routing", "best price",
            "quote comparison",
        ],
        "infrastructure": [
            "infrastructure", "middleware", "sdk", "api",
            "protocol layer", "settlement", "clearing",
        ],
    }

    best_category = "other"
    best_count = 0

    for category, keywords in categories.items():
        count = sum(1 for kw in keywords if kw in text_lower)
        if count > best_count:
            best_count = count
            best_category = category

    return best_category
