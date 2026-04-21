-- Intent-based DeFi ecosystem tracker schema

CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    slug TEXT UNIQUE,
    description TEXT,
    website TEXT,
    chains TEXT,  -- JSON array of chain names
    category TEXT,
    status TEXT DEFAULT 'active',
    token_symbol TEXT,
    coingecko_id TEXT,
    defillama_slug TEXT,
    github_org TEXT,
    twitter_handle TEXT,
    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    relevance_score REAL DEFAULT 0.0,
    is_manually_tracked INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS funding_rounds (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    round_type TEXT,
    amount_usd REAL,
    date TEXT,
    lead_investor TEXT,
    investors TEXT,  -- JSON array
    source_url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS people (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    role TEXT,
    project_id INTEGER,
    twitter_handle TEXT,
    linkedin TEXT,
    source_url TEXT,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS social_mentions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER,
    source TEXT,
    title TEXT,
    url TEXT UNIQUE,
    author TEXT,
    content_snippet TEXT,
    sentiment_score REAL,
    upvotes INTEGER DEFAULT 0,
    published_at TEXT,
    discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS github_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER,
    repo_url TEXT,
    stars INTEGER,
    forks INTEGER,
    open_issues INTEGER,
    contributors_count INTEGER,
    last_commit_at TEXT,
    commits_30d INTEGER,
    snapshot_date TEXT,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS protocol_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER,
    tvl_usd REAL,
    volume_24h REAL,
    chain TEXT,
    snapshot_date TEXT,
    source TEXT,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS scan_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scanner_name TEXT,
    started_at TIMESTAMP,
    finished_at TIMESTAMP,
    status TEXT,
    items_found INTEGER DEFAULT 0,
    error_message TEXT
);

CREATE TABLE IF NOT EXISTS discoveries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_type TEXT,
    entity_id INTEGER,
    discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    reviewed INTEGER DEFAULT 0
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_projects_name ON projects(name);
CREATE INDEX IF NOT EXISTS idx_social_mentions_url ON social_mentions(url);
CREATE INDEX IF NOT EXISTS idx_social_mentions_published_at ON social_mentions(published_at);
CREATE INDEX IF NOT EXISTS idx_github_metrics_snapshot_date ON github_metrics(snapshot_date);
CREATE INDEX IF NOT EXISTS idx_funding_rounds_project_id ON funding_rounds(project_id);
