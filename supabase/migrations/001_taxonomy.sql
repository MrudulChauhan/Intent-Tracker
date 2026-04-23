-- Migration 001 — Two-level taxonomy
-- Adds role + intent_type columns, indexes, and a CHECK constraint against
-- the canonical vocabulary. `category` is kept for backward compatibility
-- during the transition; can be dropped in a future migration after all
-- scanners and UI read from the new columns.

alter table projects
    add column if not exists role text,
    add column if not exists intent_type text;

-- Check constraints pin the vocab. Matches packages/core/taxonomy.py.
do $$ begin
    if not exists (
        select 1 from pg_constraint where conname = 'projects_role_check'
    ) then
        alter table projects
            add constraint projects_role_check
            check (role is null or role in (
                'solver','protocol','aggregator','infra','interface','tool'
            ));
    end if;
    if not exists (
        select 1 from pg_constraint where conname = 'projects_intent_type_check'
    ) then
        alter table projects
            add constraint projects_intent_type_check
            check (intent_type is null or intent_type in (
                'swap','bridge','derivatives','lending','yield','liquid_staking',
                'orderflow_auction','account_abstraction','mev','privacy',
                'launchpad','general'
            ));
    end if;
end $$;

create index if not exists idx_projects_role on projects(role);
create index if not exists idx_projects_intent_type on projects(intent_type);

-- discoveries_enriched view surfaces the old `category` as `detail`.
-- Rebuild it to include role/intent_type so the overview page can group on
-- the canonical taxonomy without a second round-trip.
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
        when d.entity_type = 'project' then coalesce(p.role, 'protocol') || '/' || coalesce(p.intent_type, 'general')
        when d.entity_type = 'social_mention' then sm.source
        when d.entity_type = 'funding_round' then fr.round_type
        else null
    end as detail,
    case when d.entity_type = 'project' then p.role end as role,
    case when d.entity_type = 'project' then p.intent_type end as intent_type
from discoveries d
left join projects p on d.entity_type = 'project' and d.entity_id = p.id
left join social_mentions sm on d.entity_type = 'social_mention' and d.entity_id = sm.id
left join funding_rounds fr on d.entity_type = 'funding_round' and d.entity_id = fr.id
left join projects fr_p on fr.project_id = fr_p.id;

grant select on discoveries_enriched to anon, authenticated, service_role;
