-- Migration 004 — Relationship graph
-- =============================================================================
-- Introduces a generic `entities` store and a typed `relationships` edge list so
-- that projects, investors, people, and integrations can be queried uniformly
-- for the /graph visualization.
--
-- Mirrors the style of 001_taxonomy.sql: idempotent, RLS-aware, public SELECT
-- only (service_role bypasses via the standard Supabase setup).
--
-- Apply via Supabase SQL Editor → paste this file → Run. Safe to re-run.
-- =============================================================================

-- ---------------------------------------------------------------------------
-- entities — unified node store
-- ---------------------------------------------------------------------------
create table if not exists entities (
    id             serial primary key,
    entity_type    text not null check (entity_type in (
        'project','investor','person','integration'
    )),
    external_id    integer,
    name           text not null,
    slug           text unique,
    metadata       jsonb,
    created_at     timestamptz default now()
);

-- Unique on (entity_type, name) so backfills are idempotent and name-based
-- lookups can't accidentally split an entity in two.
do $$ begin
    if not exists (
        select 1 from pg_constraint where conname = 'entities_type_name_key'
    ) then
        alter table entities
            add constraint entities_type_name_key unique (entity_type, name);
    end if;
end $$;

create index if not exists idx_entities_type_name on entities(entity_type, name);
create index if not exists idx_entities_external_id on entities(entity_type, external_id);

-- ---------------------------------------------------------------------------
-- relationships — typed directed edges
-- ---------------------------------------------------------------------------
create table if not exists relationships (
    id                serial primary key,
    from_id           integer not null references entities(id) on delete cascade,
    to_id             integer not null references entities(id) on delete cascade,
    relationship_type text not null check (relationship_type in (
        'invested_in','integrates_with','founded_by','acquired',
        'partnered_with','uses_solver'
    )),
    source_url        text,
    confidence        double precision default 1.0
                         check (confidence between 0 and 1),
    first_observed    timestamptz default now(),
    metadata          jsonb,
    unique (from_id, to_id, relationship_type)
);

create index if not exists idx_relationships_from on relationships(from_id, relationship_type);
create index if not exists idx_relationships_to   on relationships(to_id, relationship_type);

-- ---------------------------------------------------------------------------
-- RLS — public SELECT, writes restricted to service_role (bypasses RLS)
-- ---------------------------------------------------------------------------
alter table entities       enable row level security;
alter table relationships  enable row level security;

do $$ begin
    drop policy if exists "anon read entities"      on entities;
    drop policy if exists "anon read relationships" on relationships;
end $$;

create policy "anon read entities"      on entities      for select using (true);
create policy "anon read relationships" on relationships for select using (true);

-- ---------------------------------------------------------------------------
-- entity_degree — helper view for "top N nodes by degree" queries
-- ---------------------------------------------------------------------------
create or replace view entity_degree as
select
    e.id,
    e.entity_type,
    e.external_id,
    e.name,
    e.slug,
    coalesce(deg.degree, 0) as degree
from entities e
left join (
    select entity_id, count(*) as degree
    from (
        select from_id as entity_id from relationships
        union all
        select to_id   as entity_id from relationships
    ) all_edges
    group by entity_id
) deg on deg.entity_id = e.id;

grant select on entity_degree to anon, authenticated, service_role;

-- =============================================================================
-- Backfill from existing funding_rounds
-- -----------------------------------------------------------------------------
-- Idempotent — every INSERT is guarded by ON CONFLICT DO NOTHING.
-- 1. One `entities` row per existing project (entity_type='project').
-- 2. One `entities` row per unique lead_investor string.
-- 3. One `entities` row per investor name found inside funding_rounds.investors
--    jsonb arrays.
-- 4. `relationships` rows of type 'invested_in' for both lead and non-lead
--    investors. Lead investors get confidence=1.0, non-lead get 0.8.
-- =============================================================================
do $$
declare
    _fr record;
    _inv jsonb;
    _inv_name text;
    _investor_id int;
    _project_entity_id int;
begin
    -- 1. Projects → entities
    insert into entities (entity_type, external_id, name, slug)
    select 'project', p.id, p.name, p.slug
    from projects p
    on conflict (entity_type, name) do nothing;

    -- 2. Lead investors → entities
    insert into entities (entity_type, name)
    select distinct 'investor', trim(fr.lead_investor)
    from funding_rounds fr
    where fr.lead_investor is not null
      and length(trim(fr.lead_investor)) > 0
    on conflict (entity_type, name) do nothing;

    -- 3. Investors jsonb array → entities. funding_rounds.investors may be
    --    either ["Name A","Name B"] or [{"name":"Name A"}, ...]; handle both.
    insert into entities (entity_type, name)
    select distinct 'investor', inv_name
    from (
        select
            case jsonb_typeof(elem)
                when 'string' then trim(elem #>> '{}')
                when 'object' then trim(coalesce(elem->>'name', elem->>'investor', ''))
                else null
            end as inv_name
        from funding_rounds fr,
             lateral jsonb_array_elements(
                 case when jsonb_typeof(fr.investors) = 'array'
                      then fr.investors else '[]'::jsonb end
             ) as elem
        where fr.investors is not null
    ) s
    where inv_name is not null and length(inv_name) > 0
    on conflict (entity_type, name) do nothing;

    -- 4a. Lead-investor → project edges (confidence 1.0)
    for _fr in
        select fr.id, fr.project_id, fr.lead_investor, fr.source_url
        from funding_rounds fr
        where fr.project_id is not null
          and fr.lead_investor is not null
          and length(trim(fr.lead_investor)) > 0
    loop
        select id into _investor_id from entities
            where entity_type = 'investor' and name = trim(_fr.lead_investor);
        select id into _project_entity_id from entities
            where entity_type = 'project' and external_id = _fr.project_id;
        if _investor_id is not null and _project_entity_id is not null then
            insert into relationships
                (from_id, to_id, relationship_type, source_url, confidence)
            values
                (_investor_id, _project_entity_id, 'invested_in',
                 _fr.source_url, 1.0)
            on conflict (from_id, to_id, relationship_type) do nothing;
        end if;
    end loop;

    -- 4b. Non-lead investors (from investors jsonb) → project edges (0.8)
    for _fr in
        select fr.id, fr.project_id, fr.investors, fr.source_url
        from funding_rounds fr
        where fr.project_id is not null
          and fr.investors is not null
          and jsonb_typeof(fr.investors) = 'array'
    loop
        select id into _project_entity_id from entities
            where entity_type = 'project' and external_id = _fr.project_id;
        if _project_entity_id is null then continue; end if;

        for _inv in select * from jsonb_array_elements(_fr.investors)
        loop
            _inv_name := case jsonb_typeof(_inv)
                when 'string' then trim(_inv #>> '{}')
                when 'object' then trim(coalesce(_inv->>'name', _inv->>'investor', ''))
                else null
            end;
            if _inv_name is null or length(_inv_name) = 0 then continue; end if;

            select id into _investor_id from entities
                where entity_type = 'investor' and name = _inv_name;
            if _investor_id is null then continue; end if;

            insert into relationships
                (from_id, to_id, relationship_type, source_url, confidence)
            values
                (_investor_id, _project_entity_id, 'invested_in',
                 _fr.source_url, 0.8)
            on conflict (from_id, to_id, relationship_type) do nothing;
        end loop;
    end loop;
end $$;
