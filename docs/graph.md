# Relationship Graph

Models the intent-DeFi ecosystem as a property graph so we can answer
questions like "who co-invested in X?" and "which solvers plug into which
protocols?" without a dedicated relational schema per relationship type.

## Data model (migration `004_graph.sql`)

Two tables plus one helper view.

### `entities`
Unified node store.

| column        | type          | notes                                                                           |
|---------------|---------------|---------------------------------------------------------------------------------|
| `id`          | serial PK     |                                                                                 |
| `entity_type` | text          | one of `project`, `investor`, `person`, `integration`                           |
| `external_id` | int, nullable | for `entity_type='project'`, points at `projects.id`; unused for other types    |
| `name`        | text          | unique per `(entity_type, name)`                                                |
| `slug`        | text, unique  | optional, matches `projects.slug` when entity_type='project'                    |
| `metadata`    | jsonb         | free-form (e.g. investor HQ, AUM, website)                                      |

### `relationships`
Directed, typed edges with source + confidence.

| column              | type    | notes                                                                                           |
|---------------------|---------|-------------------------------------------------------------------------------------------------|
| `from_id` / `to_id` | int FK  | `entities.id` on delete cascade                                                                 |
| `relationship_type` | text    | `invested_in`, `integrates_with`, `founded_by`, `acquired`, `partnered_with`, `uses_solver`     |
| `source_url`        | text    | the article / SEC filing / tweet the edge was observed in                                       |
| `confidence`        | double  | 0..1 — 1.0 for lead-investor rows, 0.8 for investors pulled out of the `investors` jsonb array  |
| `first_observed`    | tstz    | when the scanner first saw the edge                                                             |
| `metadata`          | jsonb   | e.g. round amount for invested_in edges                                                         |

Unique on `(from_id, to_id, relationship_type)` — re-running the backfill is a
no-op.

### `entity_degree` (view)
Node + total edge count (in + out). The `/graph` page uses this to pick the
top-N nodes to render.

## Backfill from `funding_rounds`

The migration ends with a `DO $$ ... $$` block that does the following, all
idempotent:

1. Insert an `entities` row for every row in `projects`.
2. Insert an `entities` row for every distinct non-empty `lead_investor` in
   `funding_rounds`.
3. Walk every `funding_rounds.investors` jsonb array and add a row per investor
   name (supports both `["Name"]` and `[{"name":"Name"}]` shapes).
4. For each funding round that has both a `project_id` and a `lead_investor`,
   insert `(investor, project, 'invested_in', confidence=1.0,
   source_url=funding_rounds.source_url)`.
5. For each non-lead investor in the `investors` jsonb array, same edge at
   `confidence=0.8`.

Re-apply the migration freely — nothing is duplicated.

## Adding relationships manually

For one-off curator work, connect via the Supabase SQL Editor (service_role
only — anon is read-only):

```sql
-- 1. Make sure both endpoints exist.
insert into entities (entity_type, name)
values ('project', 'Across'), ('investor', 'Paradigm')
on conflict (entity_type, name) do nothing;

-- 2. Wire the edge.
insert into relationships
    (from_id, to_id, relationship_type, source_url, confidence)
select
    i.id, p.id, 'invested_in', 'https://paradigm.xyz/...', 1.0
from entities i, entities p
where i.entity_type='investor' and i.name='Paradigm'
  and p.entity_type='project'  and p.name='Across'
on conflict (from_id, to_id, relationship_type) do nothing;
```

From Python, use `packages/core/graph.py`:

```python
from core.supabase_writer import get_writer
from core.graph import upsert_entity, add_relationship

w = get_writer()
investor_id = upsert_entity(w, 'investor', 'Paradigm')
project_id  = upsert_entity(w, 'project',  'Across', external_id=42)
add_relationship(w, investor_id, project_id, 'invested_in',
                 source_url='https://…', confidence=1.0)
```

## Scaling past 200 nodes

The page ships with a hard cap of 200 nodes (top by degree). To grow it safely:

- **Degree cap** — already applied. Use `entity_degree` to pick the N most
  connected nodes. Edges are then filtered to ones where both endpoints made
  the cut so the sub-graph stays self-consistent.
- **Edge pruning** — drop low-confidence edges first (`confidence < 0.6`) when
  the canvas gets busy. The field is already on `relationships`.
- **Type filtering** — the existing filter strip lets the user toggle whole
  entity types off. Cheap win.
- **Community detection** — pre-compute a `cluster_id` per node with a one-off
  script (Louvain / Leiden) and filter to a single cluster when drilling in.
- **Server-side paging** — switch from "top N" to "all neighbors of X, 2-hop"
  (`api.graphForProject`) when the user drills into a project. That path is
  already wired and usually returns < 50 nodes.
- **Use `react-force-graph-3d`** or WebGL rendering for > 1000 nodes. 2D
  canvas starts to chug past that.
