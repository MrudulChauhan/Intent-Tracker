# Intent Tracker

OSINT tracker for intent-based DeFi protocols. Scans Reddit / RSS / blogs / GitHub / DefiLlama / CoinGecko / Dune, normalizes everything into a SQLite store, and serves it through a FastAPI backend and a Next.js public site.

## Monorepo layout

```
intent-tracker/
├── apps/
│   ├── api/          FastAPI backend (port 8000)
│   ├── scanner/      Scanners + scheduler + processing pipeline
│   └── web/          Next.js 16 public site (port 3000)
├── packages/
│   ├── core/         Config + DB + models + queries — the only shared Python package
│   └── brand/        Tokens + logos + CSS + guidelines — the only shared brand surface
├── data/
│   ├── intent_tracker.db       canonical SQLite file
│   └── seeds/seed_projects.py  initial project list
├── config/           Domain config (sources.py, keywords.py) — not secrets
├── scripts/          Run / bootstrap / sync shell scripts
├── tests/
├── docs/             SECURITY_AUDIT.md and other reports
├── pyproject.toml    uv-managed Python project
├── package.json      npm workspaces root
└── .env              local-only, gitignored (copy from .env.example)
```

## Getting started

```bash
cd ~/intent-tracker-v2
bash scripts/bootstrap.sh     # creates .env, installs deps, inits DB, syncs logos
```

Then fill in your keys in `.env`:

- `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET` — free at https://www.reddit.com/prefs/apps
- `GITHUB_TOKEN` — optional, raises rate limit from 60 → 5000/hr
- `DUNE_API_KEY` — optional, free tier is 2500 credits/month

## Running the stack

| Command | What |
|---|---|
| `npm run dev:api` | FastAPI on http://localhost:8000 |
| `npm run dev:web` | Next.js on http://localhost:3000 |
| `npm run scan` | One-shot scan across all scanners |
| `npm run sync-logos` | Copy `packages/brand/logos/` → `apps/web/public/logos/` |

## Where things live (one source of truth per concern)

| Concern | Single source |
|---|---|
| Env vars | `.env` (root) → loaded by `packages/core/config.py` |
| DB connection | `packages/core/db.py::get_connection()` |
| DB path | `packages/core/paths.py::DEFAULT_DB_PATH` |
| Brand tokens (colors, typography, radius) | `packages/brand/tokens.ts` + `theme.css` |
| Logos (SVG + PNG) | `packages/brand/logos/` — web copies via `sync_logos.sh` |
| Brand guidelines (prose) | `packages/brand/guidelines.md` |
| Domain config (subreddits, repo list, RSS, CoinGecko IDs) | `config/sources.py` + `config/keywords.py` |

## Changing a brand color

Update **both** files at the same time:

1. `packages/brand/tokens.ts` — TypeScript constants for `apps/web`
2. `packages/brand/theme.css` — CSS custom properties used by Tailwind

See `packages/brand/README.md` for the workflow.

## Security

See `docs/SECURITY_AUDIT.md`. Short version: tightened CORS + auth + rate limits on `/api/scan`, escaped every HTML interpolation path, pinned Python to 3.12. No known CVEs in pinned Python or npm deps (April 2026).

## Development notes

- **Next.js 16 has breaking changes from prior versions.** See `apps/web/AGENTS.md` — always check `node_modules/next/dist/docs/` before writing new patterns.
- **Python imports**: `PYTHONPATH` is set in `scripts/_env.sh` to make `core.*`, `scanners.*`, `processing.*`, and `scheduler.*` importable. All run scripts source this first.
- **Tests**: `uv run pytest` (from repo root). `tests/` is currently a placeholder.
