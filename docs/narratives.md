# Weekly narratives (P1.9)

Once a week, an LLM clusters the past 7 days of `social_mentions` into 3–5
cross-cutting themes and writes them to the `narratives` table. The overview
page ("This week's narratives") renders the most recent week.

## Components

- `supabase/migrations/003_narratives.sql` — `narratives` table + RLS
- `apps/scanner/processing/narratives.py` — loading, prompt, LLM call, validation
- `packages/core/supabase_writer.py` — `upsert_narrative`, `get_recent_narratives`
- `apps/scanner/scheduler/scheduler.py` — weekly cron + `--narratives` flag
- `apps/web/src/lib/api.ts` — `api.narratives(limit)`
- `apps/web/src/components/narratives-card.tsx` — UI card

## Enable

1. Apply the migration (Supabase SQL Editor → paste `003_narratives.sql` → Run).
2. Set two env vars on whatever host runs the scanner (GitHub Actions secrets
   for the `scan.yml` workflow, or your local `.env`):

   ```
   NARRATIVES_ENABLED=true
   ANTHROPIC_API_KEY=sk-ant-...
   ```

3. Install the new Python dep (adds `anthropic>=0.40`):

   ```
   uv sync
   ```

## Scheduling

The APScheduler job runs **Mondays at 07:00 UTC** — right after the normal
weekly scan finishes. Only registers when `NARRATIVES_ENABLED` is truthy at
scheduler startup. The job itself also re-checks the flag, so it's safe to
hot-toggle without a restart (though you'd still need a restart to register
the job for the first time).

Week boundary: the job computes `week_start = today - today.weekday()` (the
most recent Monday) and queries `discovered_at ∈ [week_start, week_start+7d)`.

## Manual re-run

```
uv run python apps/scanner/scheduler/scheduler.py --narratives
```

This runs the same code path the cron fires. Requires both env vars above.
It upserts on `(week_start, rank)`, so re-running for the current week
overwrites the previous result rather than duplicating rows.

## The prompt

System prompt is a module constant (`NARRATIVES_SYSTEM_PROMPT` in
`narratives.py`) and is marked `cache_control: ephemeral` on the wire, so
subsequent weekly runs get a prompt-cache hit on the static bit. The user
message is the rendered mention list — one line per mention, truncated to
200 chars of snippet, source and title included.

The model (`claude-haiku-4-5-20251001` — cheapest Anthropic model) is asked
to return a JSON object inside a ```json ... ``` fence:

```json
{
  "themes": [
    {
      "theme_name": "Solver economics take center stage",
      "summary": "Threads arguing solvers are the picks-and-shovels play on intent-based DeFi. UniswapX vs 1inch Fusion orderflow competition dominated.",
      "protocols": ["UniswapX", "1inch Fusion", "CoW Protocol"],
      "evidence_mention_ids": [101, 104, 102]
    }
  ]
}
```

We parse the fenced block with `json.loads` (fall back to parsing the whole
response if the fence is missing). IDs that aren't in the input list are
dropped. Themes missing `theme_name` or `summary` are skipped.

## Inspecting the prompt without calling the API

```
uv run python scripts/test_narratives_prompt.py
```

Prints the system and user prompts against a fake mention set. No network
calls, no DB access. Use this when iterating on the prompt.

## Cost

Haiku 4.5 at ~200 mentions/week is well under $0.01 per run. Prompt caching
on the system message reduces cost further after the first run.
