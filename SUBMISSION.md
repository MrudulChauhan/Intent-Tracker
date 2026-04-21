# Submission — Conviction Markets, Request for Builders V6

**Repo:** github.com/MrudulChauhan/Intent-Tracker
**Submitter:** Mrudul Chauhan — mrudulchauhan50@gmail.com
**Primary problem:** #9 Discovery and matching
**Secondary problem:** #3 Trust without institutions

---

## What this is

A working OSINT pipeline that continuously maps the **intent-based DeFi
ecosystem** — who is building what, where they are talking about it, and what
their code is doing. 125 tracked protocols, 1,790 social mentions, 2,563
discovery events as of the latest scan. Built against 8 source types:
GitHub, DefiLlama, CoinGecko, Dune, Reddit, RSS feeds, Google News, protocol
blogs.

Stack: FastAPI backend + Next.js 16 frontend + APScheduler scanner fleet
+ SQLite. Clean monorepo, 0 known CVEs (`pip-audit` + `npm audit`), hardened
per the security audit in `docs/SECURITY_AUDIT.md`.

## Why this maps to problem #9

The Request for Builders frames #9 as: *"How do problems find builders and
builders find problems? How does capital find both? Right now it's Twitter
DMs and warm intros."*

The intent-tracker is a discovery primitive for one narrow vertical (intents,
solvers, fillers, cross-chain coordination). It already does the upstream
half: **aggregate signal from where builders actually build and talk**, and
link it to protocols. With the right extensions, it becomes a matching layer
for people, capital, and problems — not just protocols.

## What's built vs. what's proposed

**Built (in this repo, working today):**
- Multi-source scanner fleet with dedup, sentiment, and relevance scoring
- Protocol graph: 125 projects with GitHub orgs, DefiLlama slugs, CoinGecko
  IDs, Twitter handles, chain coverage, funding history
- Signal layer: 1,790 deduplicated mentions linked to protocols where
  possible, sentiment-tagged, timestamped
- Public browseable site (Next.js) + API (FastAPI) for programmatic access
- Auth + rate-limited scan trigger endpoint

**Proposed (what Conviction Markets would unlock):**
- **Builder/team graph** — extract people-level signal from commits,
  authorship, blog bylines, conference decks. Follow builders across
  projects. This is the direct answer to problem #9's *builders* side.
- **Agent attribution** — distinguish human commits from agentic ones
  (GitHub Actions, claude-code bot signatures, automated PR patterns).
  Builds the foundation for Conviction Markets' hybrid-team thesis.
- **Reputation primitive** (problem #3 overlap) — portable track record
  that follows a contributor across repos, independent of employer.
- **Bidirectional matching** — capital-seeking-problems and
  problems-seeking-builders feeds, not just a search interface.

The existing scanner architecture is deliberately generic enough to widen
the aperture from "intent-based DeFi" to "any problem space Conviction
Markets cares about" — the sources and keyword taxonomies are the only
vertical-specific pieces.

## Biggest blocker

Honest version: the thing is technically functional but has no business
model, no moat (the RFP's problem #10), and no natural path from "useful
scanner I built in a weekend" to "investable primitive for a new funding
paradigm." That's the exact gap the Request for Builders describes —
shipping fast, not knowing how to make it investable. Conviction Markets'
commercialization framing + capital-in-flexible-formats is what would
unblock the next step.

## Who's building this

Mrudul Chauhan — ten years in Web3 product, currently deploying personally
into crypto. Intent-tracker is a personal side project, separate from any
employer. Contact: mrudulchauhan50@gmail.com.

## Next step

Installing the Conviction Machine GitHub app on this repo grants read
access; the code tells the full story. Happy to do a call if there's a
thread worth pulling on.
