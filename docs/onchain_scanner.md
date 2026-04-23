# On-chain Scanner (P1.5)

A Dune-powered scanner that records per-solver intent-protocol fills into
two new Supabase tables plus a manual address directory.

## Enabling

The scanner is feature-flagged **off** by default so incomplete Dune query
coverage cannot break the nightly run. To turn it on:

```bash
export ONCHAIN_SCANNER_ENABLED=true
export DUNE_API_KEY=...            # required; scanner aborts early without it
# Supabase writes still use the existing SUPABASE_URL / SUPABASE_SERVICE_KEY
```

Then run as normal:

```bash
uv run python apps/scanner/scheduler/scheduler.py --scanner onchain_dune
```

## Schema

Migration: `supabase/migrations/002_onchain.sql`.

- **`intent_fills`** — one row per on-chain fill, upserted on `tx_hash`.
- **`solver_daily_stats`** — per-(`solver_address`, `date`, `protocol`, `chain`)
  rollup over the trailing 7 days, upserted on the composite key.
- **`solvers_directory`** — manual `address → display_name` mapping. Seeded
  with 15 well-known solvers; entries flagged `NEEDS VERIFICATION` in `notes`
  must be replaced with real addresses before the directory is used for UI
  joins.

All three tables have RLS enabled with public `SELECT` and service-role-only
writes (same pattern as `supabase/schema.sql`).

## Adding a new protocol

1. Find a public Dune dashboard that filters to solver fills for the target
   protocol. Good starting points:
   - cowprotocol/solver-rewards on GitHub lists the solver addresses CoW
     maintains — build a query joining `cow_protocol.trades` to that set.
   - UniswapX: `uniswap.UniswapX_v2_evt_Fill` (Ethereum & other chains).
   - 1inch Fusion: `oneinch.fusion_evt_OrderFilled`.
   - Across v3: `across_protocol.FilledRelay`.
   - Bebop / Hashflow: each publishes public dashboards on their docs sites.
2. Fork the dashboard into your Dune workspace and edit the SELECT to project
   the exact columns documented below.
3. Save; the query's numeric ID appears in the URL
   (`dune.com/queries/<id>/...`).
4. Paste the ID into `DUNE_QUERIES` in `apps/scanner/scanners/onchain_dune.py`
   and remove the `# TODO` comment.
5. Re-run `scripts/test_onchain_dune.py` to confirm the config parses.

## Required query output columns

Each Dune query should select these columns (case-insensitive; the scanner
accepts common aliases — see `_EXPECTED_COLUMN_ALIASES`):

| Canonical name  | Accepted aliases                                    | Type               |
|-----------------|------------------------------------------------------|--------------------|
| `block_time`    | `blocktime`, `evt_block_time`, `time`, `ts`         | timestamp / epoch  |
| `tx_hash`       | `hash`, `evt_tx_hash`, `transaction_hash`           | hex string         |
| `solver`        | `solver_address`, `filler`, `resolver`              | address            |
| `chain`         | `blockchain`                                         | text (e.g. `ethereum`) |
| `amount_in_usd` | `volume_usd`, `usd_value`, `usd`                    | numeric            |
| `token_in`      | `sell_token`, `src_token`, `input_token`            | symbol or address  |
| `token_out`     | `buy_token`, `dst_token`, `output_token`            | symbol or address  |
| `user`          | `user_address`, `trader`, `owner`                   | address            |

Rows missing `tx_hash` are dropped (it's the upsert key). Rows with
unparseable `block_time` are still inserted, but excluded from the 7-day
rollup.

## Post-first-run verification

After the first successful run, check:

1. **Row counts** — `select count(*) from intent_fills` should be non-zero
   for any protocol whose Dune query returned rows. Log output from
   `scheduler` shows the per-protocol breakdown.
2. **Rollup freshness** — `select max(date) from solver_daily_stats` should
   be today (UTC) or yesterday.
3. **Directory hygiene** — cross-check the addresses returned in
   `intent_fills.solver_address` against `solvers_directory`. Unknowns
   should be added manually; placeholders flagged `NEEDS VERIFICATION`
   should be replaced with the real addresses.
4. **Dune credit usage** — the scanner uses `get_latest_result`, which reads
   cached executions and does **not** burn execution credits. Confirm your
   Dune account's credit counter hasn't moved.
5. **Scan log** — `select * from scan_log where scanner_name = 'onchain_dune'
   order by started_at desc limit 5;` — status should be `success`;
   `items_found` reflects fills inserted.

## Non-goals

- No leaderboard UI yet (that's P1.6).
- No direct-RPC indexing — Dune only until we outgrow it.
- No automatic discovery of new solver addresses — update
  `solvers_directory` manually.
