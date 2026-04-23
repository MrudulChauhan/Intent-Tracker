# Twitter / X Scanner (P1.4)

One-page operator guide for the `TwitterScanner` daily job.

## Why `twikit` and not the official X API

- **Official X API v2** is paywalled. The Basic tier ($100+/month) caps
  user-timeline lookups far below what we need for ~50 seeds/day, and the
  Free tier doesn't expose `GET /users/:id/tweets` at all.
- **HTML scraping** (e.g. `snscrape`, headless browsers) is brittle --
  X's gnf.js bundle changes every few weeks and every scraper project has
  had multi-week outages in 2024-2025.
- **`twikit`** uses the same internal GraphQL endpoints the X web app
  uses, authenticated with a real session cookie. Stable as long as the
  underlying account stays unbanned, and free.

The tradeoff is ToS + ban risk (see below).

## Account setup (one-time)

1. Create a **throwaway** X account. Do not use your primary. Use a
   fresh email alias and a fresh phone number.
2. Log into it via the X web app once, complete any "verify your email"
   / "verify your phone" prompts, and accept any device challenges.
3. In the repo root, copy `.env.example` to `.env` if you haven't, and
   fill in:
   ```
   X_USERNAME=<throwaway handle, no @>
   X_EMAIL=<throwaway email>
   X_PASSWORD=<throwaway password>
   X_COOKIES_FILE=./data/x_cookies.json
   ```
4. Run the login helper exactly once to bake cookies:
   ```
   uv run python scripts/twitter_login.py
   ```
   This writes `data/x_cookies.json` (gitignored). After this, the
   scanner reads the cookies file and never needs the password again.
5. Optionally clear `X_PASSWORD` from `.env` once cookies are saved,
   to shrink the secret surface area.

## Enabling the scanner

Flip the feature flag in `.env`:

```
TWITTER_SCANNER_ENABLED=true
```

On the next scheduled run the scanner will register itself in
`apps/scanner/scheduler/scheduler.py` after the other content scanners
(rss, reddit, google_news) and emit mentions with `source='twitter'` to
the existing `social_mentions` table. No new table, no new schema.

Manual one-off invocation:

```
uv run python apps/scanner/scheduler/scheduler.py --scanner twitter
```

## ToS / ban risk

- twikit is **not** an officially sanctioned API client. Heavy use
  (hundreds of requests per minute, aggressive concurrency, follows,
  likes) gets accounts suspended quickly.
- The defaults here are deliberately conservative: ~50 seeds * 20
  tweets = 1000 tweets max per daily run, 1-second spacing between
  seeds, exponential backoff on `TooManyRequests`. **Do not raise these
  numbers** without a reason.
- Expect to rotate accounts every few months. When a ban happens:
  1. Create a new throwaway account (fresh email, fresh phone).
  2. Delete `data/x_cookies.json`.
  3. Re-run `scripts/twitter_login.py`.
  4. No code changes needed; cookies rotate in place.

## Adding or removing seed accounts

Seeds live in `config/twitter_seeds.py` under `SEED_ACCOUNTS`, grouped
by category (`protocols`, `solvers`, `research`, `orderflow`,
`bridges`). A "useful" seed is an account that posts intent-DeFi content
at least once a month. See the module docstring for the full rotation
policy.

Workflow:

1. Edit `config/twitter_seeds.py`, add the bare handle (no `@`) in the
   right category list.
2. Run the dry-run checker:
   ```
   uv run python scripts/test_twitter_scanner.py
   ```
3. Commit with a one-line rationale ("Add @someone: shipping solver
   research weekly since March").

To prune dead seeds, query `social_mentions` for `source='twitter'`
grouped by `author` -- handles with zero mentions in the last 60 days
are candidates for removal.

## Troubleshooting

- **`TwitterScanner requires either X_COOKIES_FILE ...`**: env vars
  aren't loaded or cookies file doesn't exist. Re-run the login script.
- **`twikit.errors.Unauthorized`**: cookies expired. Delete
  `data/x_cookies.json` and re-run `scripts/twitter_login.py`.
- **`TooManyRequests` logged repeatedly**: account is being throttled.
  Reduce `TWEETS_PER_SEED` in the scanner module or wait a few hours
  before the next run.
- **Account suspended**: see "rotate accounts" above; the project is
  designed to assume this will happen periodically.
