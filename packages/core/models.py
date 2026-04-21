"""Dataclass models for the intent-based DeFi ecosystem tracker."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Project:
    id: Optional[int] = None
    name: str = ""
    slug: Optional[str] = None
    description: Optional[str] = None
    website: Optional[str] = None
    chains: Optional[str] = None  # JSON array
    category: Optional[str] = None
    status: str = "active"
    token_symbol: Optional[str] = None
    coingecko_id: Optional[str] = None
    defillama_slug: Optional[str] = None
    github_org: Optional[str] = None
    twitter_handle: Optional[str] = None
    first_seen: Optional[str] = None
    last_updated: Optional[str] = None
    relevance_score: float = 0.0
    is_manually_tracked: int = 0


@dataclass
class FundingRound:
    id: Optional[int] = None
    project_id: int = 0
    round_type: Optional[str] = None
    amount_usd: Optional[float] = None
    date: Optional[str] = None
    lead_investor: Optional[str] = None
    investors: Optional[str] = None  # JSON array
    source_url: Optional[str] = None
    created_at: Optional[str] = None


@dataclass
class Person:
    id: Optional[int] = None
    name: str = ""
    role: Optional[str] = None
    project_id: Optional[int] = None
    twitter_handle: Optional[str] = None
    linkedin: Optional[str] = None
    source_url: Optional[str] = None


@dataclass
class SocialMention:
    id: Optional[int] = None
    project_id: Optional[int] = None
    source: Optional[str] = None
    title: Optional[str] = None
    url: Optional[str] = None
    author: Optional[str] = None
    content_snippet: Optional[str] = None
    sentiment_score: Optional[float] = None
    upvotes: int = 0
    published_at: Optional[str] = None
    discovered_at: Optional[str] = None


@dataclass
class GithubMetric:
    id: Optional[int] = None
    project_id: int = 0
    repo_url: Optional[str] = None
    stars: Optional[int] = None
    forks: Optional[int] = None
    open_issues: Optional[int] = None
    contributors_count: Optional[int] = None
    last_commit_at: Optional[str] = None
    commits_30d: Optional[int] = None
    snapshot_date: Optional[str] = None


@dataclass
class ProtocolMetric:
    id: Optional[int] = None
    project_id: int = 0
    tvl_usd: Optional[float] = None
    volume_24h: Optional[float] = None
    chain: Optional[str] = None
    snapshot_date: Optional[str] = None
    source: Optional[str] = None


@dataclass
class ScanLogEntry:
    id: Optional[int] = None
    scanner_name: Optional[str] = None
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    status: Optional[str] = None
    items_found: int = 0
    error_message: Optional[str] = None


@dataclass
class Discovery:
    id: Optional[int] = None
    entity_type: Optional[str] = None
    entity_id: Optional[int] = None
    discovered_at: Optional[str] = None
    reviewed: int = 0
