-- Intent Tracker — Migration 003: weekly narratives (P1.9)
-- =============================================================================
-- Adds a `narratives` table that stores LLM-generated theme clusters over the
-- past 7 days of social_mentions. One row per (week_start, rank).
--
-- Style mirrors supabase/schema.sql and migration 001_taxonomy.sql:
--   - idempotent (IF NOT EXISTS, DROP POLICY IF EXISTS)
--   - RLS enabled, public SELECT, writes implicitly limited to service_role
--
-- Apply via Supabase SQL Editor → paste this file → Run.
-- =============================================================================

create table if not exists narratives (
    id                    serial primary key,
    week_start            date not null,
    rank                  integer,
    theme                 text,
    summary               text,
    protocols_mentioned   jsonb,
    evidence_mention_ids  jsonb,
    model_used            text,
    created_at            timestamptz default now(),
    unique (week_start, rank)
);

-- Primary access pattern: "give me the latest week's narratives, ordered by rank"
create index if not exists idx_narratives_week_start on narratives(week_start desc);

-- =============================================================================
-- Row-Level Security
-- =============================================================================
alter table narratives enable row level security;

do $$ begin
    drop policy if exists "anon read narratives" on narratives;
end $$;

create policy "anon read narratives" on narratives for select using (true);

-- No INSERT/UPDATE/DELETE policies → only service_role (which bypasses RLS)
-- can write. This matches the pattern used by every other table in this schema.
