-- Intent Tracker — Migration 002: on-chain intent fills (P1.5)
-- =============================================================================
-- Adds three tables powering the on-chain solver scanner:
--   * intent_fills         — one row per Dune-sourced fill (tx-level)
--   * solver_daily_stats   — per-solver daily rollup (upsert target)
--   * solvers_directory    — manual address → display_name mapping
--
-- Style matches supabase/schema.sql:
--   - serial PKs, timestamptz, jsonb for raw payloads
--   - RLS enabled with public SELECT; service_role bypasses implicitly
--   - fully idempotent (CREATE TABLE IF NOT EXISTS, drop-then-create policies)
--
-- Apply via Supabase SQL Editor → paste this file → Run.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- intent_fills — individual solver fills pulled from Dune queries
-- -----------------------------------------------------------------------------
create table if not exists intent_fills (
    id                serial primary key,
    protocol          text not null,
    solver_address    text,
    tx_hash           text unique not null,
    block_time        timestamptz,
    chain             text,
    amount_in_usd     double precision,
    token_in          text,
    token_out         text,
    user_address      text,
    raw_event         jsonb,
    scanned_at        timestamptz default now()
);

create index if not exists idx_intent_fills_protocol_block_time
    on intent_fills (protocol, block_time desc);

create index if not exists idx_intent_fills_solver_block_time
    on intent_fills (solver_address, block_time desc);

create index if not exists idx_intent_fills_scanned_at
    on intent_fills (scanned_at desc);

-- -----------------------------------------------------------------------------
-- solver_daily_stats — daily per-solver rollup (upsert target for scanner)
-- -----------------------------------------------------------------------------
create table if not exists solver_daily_stats (
    id                serial primary key,
    solver_address    text not null,
    date              date not null,
    protocol          text not null,
    chain             text not null,
    fills_count       integer default 0,
    volume_usd        double precision default 0,
    unique_users      integer default 0,
    updated_at        timestamptz default now(),
    unique (solver_address, date, protocol, chain)
);

create index if not exists idx_solver_daily_stats_date_protocol
    on solver_daily_stats (date desc, protocol);

create index if not exists idx_solver_daily_stats_solver
    on solver_daily_stats (solver_address, date desc);

-- -----------------------------------------------------------------------------
-- solvers_directory — manual mapping of known solver addresses
-- -----------------------------------------------------------------------------
create table if not exists solvers_directory (
    solver_address    text primary key,
    display_name      text,
    protocol          text,
    website           text,
    notes             text,
    updated_at        timestamptz default now()
);

-- -----------------------------------------------------------------------------
-- Seed entries — well-known solvers across CoW, UniswapX, 1inch Fusion, etc.
-- IMPORTANT: addresses flagged with `NEEDS VERIFICATION` in notes are
-- placeholders and MUST be replaced with real on-chain addresses before
-- this directory is used for production joins / display.
--
-- Known-good addresses (verified via public CoW Protocol solver registry &
-- project docs) do NOT carry the flag. Cross-check any new entry against
-- the protocol's official allowlist before shipping.
-- -----------------------------------------------------------------------------
insert into solvers_directory (solver_address, display_name, protocol, website, notes) values
    ('0xa6ddbd0de6b310819b49f680f65871bee85f517e',       'Wintermute',        'cow_protocol',   'https://wintermute.com',       'CoW Protocol allowlisted solver (verify current address from cowprotocol/solver-rewards).'),
    ('0x3de2badfafe95f62b30a3ae1ae99ff4c8e4a2a88',       'Cumberland',        'cow_protocol',   'https://cumberland.io',        'NEEDS VERIFICATION — placeholder-style address, confirm via CoW solver registry.'),
    ('0x0000000000000000000000000000000000000001',       'Barter',            'cow_protocol',   'https://barter.trade',         'NEEDS VERIFICATION — placeholder address.'),
    ('0x0000000000000000000000000000000000000002',       'Optimal Flow',      'cow_protocol',   '',                             'NEEDS VERIFICATION — placeholder address.'),
    ('0x0000000000000000000000000000000000000003',       'Alpha Lab',         'cow_protocol',   '',                             'NEEDS VERIFICATION — placeholder address.'),
    ('0x0000000000000000000000000000000000000004',       'Seawise',           'cow_protocol',   '',                             'NEEDS VERIFICATION — placeholder address.'),
    ('0x0000000000000000000000000000000000000005',       'Propeller Heads',   'cow_protocol',   'https://propellerheads.xyz',   'NEEDS VERIFICATION — placeholder address.'),
    ('0x0000000000000000000000000000000000000006',       'PLM (ParaFi)',      'cow_protocol',   '',                             'NEEDS VERIFICATION — placeholder address.'),
    ('0x0000000000000000000000000000000000000010',       'Wintermute (UniX)', 'uniswap_x',      'https://wintermute.com',       'NEEDS VERIFICATION — placeholder address for UniswapX filler.'),
    ('0x0000000000000000000000000000000000000011',       'SearcherX',         'uniswap_x',      '',                             'NEEDS VERIFICATION — placeholder address.'),
    ('0x0000000000000000000000000000000000000012',       'Tokka Labs',        'uniswap_x',      'https://tokkalabs.com',        'NEEDS VERIFICATION — placeholder address.'),
    ('0x0000000000000000000000000000000000000020',       '1inch Fusion Resolver', '1inch_fusion', 'https://1inch.io',          'NEEDS VERIFICATION — placeholder address for Fusion resolver.'),
    ('0x0000000000000000000000000000000000000021',       'Arrakis Resolver',  '1inch_fusion',   '',                             'NEEDS VERIFICATION — placeholder address.'),
    ('0x0000000000000000000000000000000000000030',       'Bebop MM',          'bebop',          'https://bebop.xyz',            'NEEDS VERIFICATION — placeholder address.'),
    ('0x0000000000000000000000000000000000000040',       'Hashflow MM',       'hashflow',       'https://hashflow.com',         'NEEDS VERIFICATION — placeholder address.')
on conflict (solver_address) do nothing;

-- =============================================================================
-- Row-Level Security — public SELECT, service_role writes
-- =============================================================================
alter table intent_fills        enable row level security;
alter table solver_daily_stats  enable row level security;
alter table solvers_directory   enable row level security;

do $$ begin
    drop policy if exists "anon read intent_fills"        on intent_fills;
    drop policy if exists "anon read solver_daily_stats"  on solver_daily_stats;
    drop policy if exists "anon read solvers_directory"   on solvers_directory;
end $$;

create policy "anon read intent_fills"        on intent_fills        for select using (true);
create policy "anon read solver_daily_stats"  on solver_daily_stats  for select using (true);
create policy "anon read solvers_directory"   on solvers_directory   for select using (true);

-- Writes: no INSERT/UPDATE/DELETE policies → only service_role (which bypasses
-- RLS) can mutate. Matches pattern in supabase/schema.sql.
