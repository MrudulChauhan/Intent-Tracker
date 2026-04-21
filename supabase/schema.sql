-- Intent Tracker — Supabase (Postgres) schema
-- =============================================================================
-- Port of packages/core/schema.sql (SQLite) to Postgres, with:
--   - serial PKs instead of AUTOINCREMENT
--   - timestamptz instead of TIMESTAMP
--   - jsonb instead of TEXT for chains/investors arrays
--   - RLS enabled with public SELECT, service_role bypasses implicitly
--   - discoveries_enriched VIEW to replace the client-side JOIN the old FastAPI did
--
-- Apply via Supabase SQL Editor → paste this file → Run.
-- Idempotent (uses CREATE TABLE IF NOT EXISTS, CREATE OR REPLACE VIEW, etc.)
-- =============================================================================

create table if not exists projects (
    id               serial primary key,
    name             text unique not null,
    slug             text unique,
    description      text,
    website          text,
    chains           jsonb,
    category         text,
    status           text default 'active',
    token_symbol     text,
    coingecko_id     text,
    defillama_slug   text,
    github_org       text,
    twitter_handle   text,
    first_seen       timestamptz default now(),
    last_updated     timestamptz default now(),
    relevance_score  double precision default 0.0,
    is_manually_tracked  integer default 0
);

create table if not exists funding_rounds (
    id              serial primary key,
    project_id      integer references projects(id) on delete cascade,
    round_type      text,
    amount_usd      double precision,
    date            text,
    lead_investor   text,
    investors       jsonb,
    source_url      text,
    created_at      timestamptz default now()
);

create table if not exists people (
    id              serial primary key,
    name            text not null,
    role            text,
    project_id      integer references projects(id) on delete set null,
    twitter_handle  text,
    linkedin        text,
    source_url      text
);

create table if not exists social_mentions (
    id                serial primary key,
    project_id        integer references projects(id) on delete set null,
    source            text,
    title             text,
    url               text unique,
    author            text,
    content_snippet   text,
    sentiment_score   double precision,
    upvotes           integer default 0,
    published_at      text,
    discovered_at     timestamptz default now()
);

create table if not exists github_metrics (
    id                     serial primary key,
    project_id             integer references projects(id) on delete cascade,
    repo_url               text,
    stars                  integer,
    forks                  integer,
    open_issues            integer,
    contributors_count     integer,
    last_commit_at         text,
    commits_30d            integer,
    snapshot_date          text
);

create table if not exists protocol_metrics (
    id              serial primary key,
    project_id      integer references projects(id) on delete cascade,
    tvl_usd         double precision,
    volume_24h      double precision,
    chain           text,
    snapshot_date   text,
    source          text
);

create table if not exists scan_log (
    id              serial primary key,
    scanner_name    text,
    started_at      timestamptz,
    finished_at     timestamptz,
    status          text,
    items_found     integer default 0,
    error_message   text
);

create table if not exists discoveries (
    id              serial primary key,
    entity_type     text,
    entity_id       integer,
    discovered_at   timestamptz default now(),
    reviewed        integer default 0
);

-- Indexes
create index if not exists idx_projects_name on projects(name);
create index if not exists idx_social_mentions_url on social_mentions(url);
create index if not exists idx_social_mentions_published_at on social_mentions(published_at);
create index if not exists idx_github_metrics_snapshot_date on github_metrics(snapshot_date);
create index if not exists idx_funding_rounds_project_id on funding_rounds(project_id);
create index if not exists idx_discoveries_reviewed on discoveries(reviewed);
create index if not exists idx_discoveries_discovered_at on discoveries(discovered_at desc);

-- =============================================================================
-- View: discoveries_enriched
-- Replaces the multi-JOIN SELECT that FastAPI used to do client-side.
-- The anon role can SELECT this view; the joins happen server-side.
-- =============================================================================
create or replace view discoveries_enriched as
select
    d.id,
    d.entity_type,
    d.entity_id,
    d.discovered_at,
    d.reviewed,
    case
        when d.entity_type = 'project' then p.name
        when d.entity_type = 'social_mention' then sm.title
        when d.entity_type = 'funding_round' then fr_p.name
        else 'Unknown'
    end as name,
    case
        when d.entity_type = 'project' then p.category
        when d.entity_type = 'social_mention' then sm.source
        when d.entity_type = 'funding_round' then fr.round_type
        else null
    end as detail
from discoveries d
left join projects p on d.entity_type = 'project' and d.entity_id = p.id
left join social_mentions sm on d.entity_type = 'social_mention' and d.entity_id = sm.id
left join funding_rounds fr on d.entity_type = 'funding_round' and d.entity_id = fr.id
left join projects fr_p on fr.project_id = fr_p.id;

-- =============================================================================
-- Row-Level Security
-- =============================================================================
-- Public read on every data table. Writes are service_role only (bypasses RLS).
-- No policies for INSERT/UPDATE/DELETE means anon gets 401 on writes by design.

alter table projects           enable row level security;
alter table funding_rounds     enable row level security;
alter table people             enable row level security;
alter table social_mentions    enable row level security;
alter table github_metrics     enable row level security;
alter table protocol_metrics   enable row level security;
alter table scan_log           enable row level security;
alter table discoveries        enable row level security;

-- Drop-if-exists pattern so this script is idempotent
do $$ begin
    drop policy if exists "anon read projects"          on projects;
    drop policy if exists "anon read funding_rounds"    on funding_rounds;
    drop policy if exists "anon read people"            on people;
    drop policy if exists "anon read social_mentions"   on social_mentions;
    drop policy if exists "anon read github_metrics"    on github_metrics;
    drop policy if exists "anon read protocol_metrics"  on protocol_metrics;
    drop policy if exists "anon read scan_log"          on scan_log;
    drop policy if exists "anon read discoveries"       on discoveries;
end $$;

create policy "anon read projects"          on projects          for select using (true);
create policy "anon read funding_rounds"    on funding_rounds    for select using (true);
create policy "anon read people"            on people            for select using (true);
create policy "anon read social_mentions"   on social_mentions   for select using (true);
create policy "anon read github_metrics"    on github_metrics    for select using (true);
create policy "anon read protocol_metrics"  on protocol_metrics  for select using (true);
create policy "anon read scan_log"          on scan_log          for select using (true);
create policy "anon read discoveries"       on discoveries       for select using (true);

-- discoveries_enriched is a view over policy-protected tables; access inherits.
-- Grant so PostgREST exposes it.
grant select on discoveries_enriched to anon, authenticated, service_role;
