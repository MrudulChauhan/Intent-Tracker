"""LLM-powered weekly narrative clustering over social_mentions.

Once a week, this module:
  1. Loads ~100-300 social_mentions from the past 7 days
  2. Builds a compact prompt (title + source + 200-char snippet per mention)
  3. Calls Claude Haiku with prompt caching on the (fixed) system prompt
  4. Parses the JSON response into 3-5 themes
  5. Persists each theme as a row in the `narratives` table

Design notes:
  - Model: claude-haiku-4-5-20251001 (cheapest, good enough for clustering).
  - Prompt caching: the SYSTEM prompt is static across weekly runs, so we mark
    it with `cache_control={"type": "ephemeral"}`. The user message (weekly
    mention set) is not cached — it changes every run.
  - Structured output: we ask for a ```json ... ``` fenced block and parse with
    json.loads on the extracted substring. This is more robust across model
    versions than relying on tool-use for a single call.
  - No external network at import time. The anthropic SDK is imported lazily
    inside `generate_weekly_narratives` so `scripts/test_narratives_prompt.py`
    can render the prompt without the dependency installed.
"""

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any, Optional


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: Model pinned for weekly narrative generation. Haiku 4.5 is the cheapest
#: Anthropic model with strong-enough reasoning for this clustering job.
NARRATIVES_MODEL: str = "claude-haiku-4-5-20251001"

#: Max snippet length per mention included in the prompt. Keeps total tokens
#: manageable when we pass ~200 mentions in one call.
MAX_SNIPPET_CHARS: int = 200

#: Soft upper bound on mentions included in the prompt. If we load more, we
#: truncate (oldest first) to stay within a reasonable context window.
MAX_MENTIONS_IN_PROMPT: int = 300

#: Minimum mentions needed before we bother calling the LLM.
MIN_MENTIONS_FOR_LLM: int = 5

#: Static system prompt — kept in a module constant so it's easy to iterate
#: AND so prompt-caching works (Anthropic caches on exact-match prefix).
NARRATIVES_SYSTEM_PROMPT: str = """You are a DeFi research analyst clustering social mentions into weekly narrative themes.

You will receive a list of social mentions (title + source + snippet) from the past 7 days, each with a numeric ID. Your job is to identify the 3-5 most prominent THEMES (not individual stories) discussed across the mentions, and for each theme return:

  - theme_name: a short, punchy label (max 6 words, title case)
  - summary: 1-2 sentences describing the theme in plain English
  - protocols: a list of protocol / project names mentioned under this theme (dedupe, canonicalize casing)
  - evidence_mention_ids: up to 5 mention IDs from the input that best support this theme

Rules:
  - Pick themes that are genuinely cross-cutting (appear in >=3 mentions). Do NOT create a theme for a single post.
  - Rank themes by prominence (most discussed first).
  - Protocol names: prefer the canonical form (e.g. "CoW Protocol" not "cow swap").
  - Return between 3 and 5 themes. If the input truly only supports 2, return 2.
  - The evidence_mention_ids MUST be integers from the provided input list — do not invent IDs.

Output format: return ONLY a JSON object inside a ```json ... ``` fenced code block. No prose before or after. The JSON schema is:

{
  "themes": [
    {
      "theme_name": "string",
      "summary": "string",
      "protocols": ["string", ...],
      "evidence_mention_ids": [int, ...]
    },
    ...
  ]
}
"""


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass
class Narrative:
    """In-memory representation of one theme, pre-persistence."""

    week_start: date
    rank: int
    theme: str
    summary: str
    protocols_mentioned: list[str] = field(default_factory=list)
    evidence_mention_ids: list[int] = field(default_factory=list)
    model_used: str = NARRATIVES_MODEL

    def to_row(self) -> dict[str, Any]:
        """Serialize for the `narratives` Supabase table."""
        return {
            "week_start": self.week_start.isoformat(),
            "rank": self.rank,
            "theme": self.theme,
            "summary": self.summary,
            "protocols_mentioned": self.protocols_mentioned,
            "evidence_mention_ids": self.evidence_mention_ids,
            "model_used": self.model_used,
        }


# ---------------------------------------------------------------------------
# Mention loading
# ---------------------------------------------------------------------------


def _load_mentions_sqlite(conn: Any, start: datetime, end: datetime) -> list[dict]:
    """Fetch mentions from a DB-API SQLite connection."""
    cur = conn.execute(
        """
        SELECT id, source, title, content_snippet, url
        FROM social_mentions
        WHERE discovered_at >= ? AND discovered_at < ?
        ORDER BY discovered_at DESC
        LIMIT ?
        """,
        (start.isoformat(), end.isoformat(), MAX_MENTIONS_IN_PROMPT),
    )
    rows = cur.fetchall()
    return [
        {
            "id": r[0],
            "source": r[1] or "",
            "title": r[2] or "",
            "content_snippet": r[3] or "",
            "url": r[4] or "",
        }
        for r in rows
    ]


def _load_mentions_supabase(writer: Any, start: datetime, end: datetime) -> list[dict]:
    """Fetch mentions via a SupabaseWriter's httpx client.

    We hit PostgREST directly rather than adding a dedicated method because
    this is a read-only path used only here.
    """
    url = f"{writer.base}/social_mentions"
    params = {
        "select": "id,source,title,content_snippet,url",
        "discovered_at": f"gte.{start.isoformat()}",
        "order": "discovered_at.desc",
        "limit": str(MAX_MENTIONS_IN_PROMPT),
    }
    # httpx doesn't support repeating param keys via dict — use a tuple list
    param_pairs = list(params.items()) + [
        ("discovered_at", f"lt.{end.isoformat()}"),
    ]
    resp = writer.client.get(url, params=param_pairs)
    if resp.status_code >= 400:
        logger.warning(
            "Supabase read social_mentions failed (%d): %s",
            resp.status_code, resp.text[:200],
        )
        return []
    return resp.json() or []


def _load_mentions(conn_or_writer: Any, week_start: date) -> list[dict]:
    """Route mention loading to the right backend.

    Accepts either a SQLite connection (has `.execute`) or a SupabaseWriter
    (has `.base` and `.client`).
    """
    start = datetime.combine(week_start, datetime.min.time())
    end = start + timedelta(days=7)

    if hasattr(conn_or_writer, "base") and hasattr(conn_or_writer, "client"):
        return _load_mentions_supabase(conn_or_writer, start, end)
    if hasattr(conn_or_writer, "execute"):
        return _load_mentions_sqlite(conn_or_writer, start, end)
    raise TypeError(
        f"Unsupported conn_or_writer type: {type(conn_or_writer).__name__}. "
        "Expected a sqlite3.Connection or a SupabaseWriter."
    )


# ---------------------------------------------------------------------------
# Prompt rendering
# ---------------------------------------------------------------------------


def _truncate(text: str, limit: int) -> str:
    text = (text or "").strip().replace("\n", " ")
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def render_mentions_prompt(mentions: list[dict], week_start: date) -> str:
    """Render the USER message content for the LLM call.

    Separate from the system prompt so the system prompt can be cached.
    """
    lines: list[str] = [
        f"Week start: {week_start.isoformat()} (covers 7 days).",
        f"Total mentions: {len(mentions)}.",
        "",
        "Mentions (id | source | title | snippet):",
    ]
    for m in mentions:
        mid = m.get("id")
        source = _truncate(m.get("source", ""), 40)
        title = _truncate(m.get("title", ""), 160)
        snippet = _truncate(m.get("content_snippet", ""), MAX_SNIPPET_CHARS)
        lines.append(f"[{mid}] {source} | {title} | {snippet}")
    lines.append("")
    lines.append(
        "Now identify 3-5 cross-cutting themes and return the JSON object "
        "as specified in the system prompt."
    )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# LLM call + response parsing
# ---------------------------------------------------------------------------


_JSON_FENCE_RE = re.compile(r"```json\s*(\{.*?\})\s*```", re.DOTALL | re.IGNORECASE)


def _extract_json_block(text: str) -> Optional[dict]:
    """Pull the first ```json ... ``` block out of the model's response."""
    if not text:
        return None
    m = _JSON_FENCE_RE.search(text)
    if not m:
        # Fallback: try to parse the whole response as JSON (some models
        # occasionally drop the fence).
        try:
            return json.loads(text.strip())
        except json.JSONDecodeError:
            return None
    try:
        return json.loads(m.group(1))
    except json.JSONDecodeError as exc:
        logger.warning("Failed to parse JSON block from LLM response: %s", exc)
        return None


def _call_claude(user_prompt: str) -> Optional[str]:
    """Call Claude Haiku with prompt caching on the system message.

    Returns the assistant text, or None on failure.
    Raises RuntimeError if ANTHROPIC_API_KEY is unset.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY is not set. Narratives require an Anthropic "
            "API key — set it in the scanner's environment."
        )

    try:
        from anthropic import Anthropic  # type: ignore[import-not-found]
    except ImportError as exc:
        raise RuntimeError(
            "The `anthropic` package is not installed. Run "
            "`uv sync` (or `uv pip install 'anthropic>=0.40'`) after pulling."
        ) from exc

    client = Anthropic(api_key=api_key)

    try:
        resp = client.messages.create(
            model=NARRATIVES_MODEL,
            max_tokens=2048,
            system=[
                {
                    "type": "text",
                    "text": NARRATIVES_SYSTEM_PROMPT,
                    # Cache the static system prompt across weekly runs.
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[{"role": "user", "content": user_prompt}],
        )
    except Exception as exc:  # broad: SDK may raise various network/API errors
        logger.exception("Anthropic API call failed: %s", exc)
        return None

    # resp.content is a list of content blocks; grab the first text block.
    for block in getattr(resp, "content", []) or []:
        if getattr(block, "type", None) == "text":
            return getattr(block, "text", "") or ""
    logger.warning("Anthropic response had no text block")
    return None


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def _validate_themes(
    parsed: dict, valid_ids: set[int], week_start: date
) -> list[Narrative]:
    """Turn the parsed LLM dict into a list of Narrative objects.

    Drops themes that fail validation rather than raising — we'd rather
    persist 3 good themes than reject the batch because one was malformed.
    """
    themes = parsed.get("themes") if isinstance(parsed, dict) else None
    if not isinstance(themes, list):
        logger.warning("LLM response missing 'themes' list")
        return []

    out: list[Narrative] = []
    for i, t in enumerate(themes[:5], start=1):
        if not isinstance(t, dict):
            continue
        name = str(t.get("theme_name") or "").strip()
        summary = str(t.get("summary") or "").strip()
        if not name or not summary:
            logger.warning("Skipping theme #%d: missing name or summary", i)
            continue

        raw_protocols = t.get("protocols") or []
        protocols = [
            str(p).strip() for p in raw_protocols
            if isinstance(p, (str, int)) and str(p).strip()
        ]

        raw_ids = t.get("evidence_mention_ids") or []
        evidence: list[int] = []
        for mid in raw_ids:
            try:
                mid_int = int(mid)
            except (TypeError, ValueError):
                continue
            if mid_int in valid_ids:
                evidence.append(mid_int)
            if len(evidence) >= 5:
                break

        out.append(
            Narrative(
                week_start=week_start,
                rank=i,
                theme=name,
                summary=summary,
                protocols_mentioned=protocols,
                evidence_mention_ids=evidence,
            )
        )
    return out


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def generate_weekly_narratives(
    conn_or_writer: Any, week_start: date
) -> list[Narrative]:
    """Cluster the past 7 days of social_mentions into 3-5 themes.

    Args:
        conn_or_writer: either a sqlite3 Connection or a SupabaseWriter. The
            former is used in local/dev mode; the latter in production where
            the scanner targets Supabase.
        week_start: the Monday (or any date) that starts the 7-day window.

    Returns:
        List of persisted Narrative objects, ordered by rank. Empty list if
        there weren't enough mentions or the LLM call failed.

    Raises:
        RuntimeError: if ANTHROPIC_API_KEY is not set AND we have enough
            mentions to call the LLM. (Empty mention sets return [] without
            raising, so it's safe to call this on a quiet week.)
    """
    logger.info("Generating narratives for week_start=%s", week_start.isoformat())
    mentions = _load_mentions(conn_or_writer, week_start)
    logger.info("Loaded %d mentions for the week", len(mentions))

    if len(mentions) < MIN_MENTIONS_FOR_LLM:
        logger.info(
            "Only %d mentions this week (< %d). Skipping LLM call.",
            len(mentions), MIN_MENTIONS_FOR_LLM,
        )
        return []

    user_prompt = render_mentions_prompt(mentions, week_start)
    raw = _call_claude(user_prompt)
    if not raw:
        logger.warning("LLM returned no content; no narratives persisted.")
        return []

    parsed = _extract_json_block(raw)
    if not parsed:
        logger.warning("Could not extract JSON block from LLM response.")
        return []

    valid_ids = {int(m["id"]) for m in mentions if m.get("id") is not None}
    narratives = _validate_themes(parsed, valid_ids, week_start)
    if not narratives:
        logger.warning("Validation produced zero narratives.")
        return []

    # Persist if the writer knows how. SQLite connections currently don't —
    # in that code path we just return the in-memory list.
    persisted: list[Narrative] = []
    for n in narratives:
        try:
            if hasattr(conn_or_writer, "upsert_narrative"):
                conn_or_writer.upsert_narrative(n.to_row())
                persisted.append(n)
            else:
                # SQLite fallback: best-effort INSERT. Schema may not exist
                # locally yet; don't let that break the run.
                try:
                    conn_or_writer.execute(
                        """
                        INSERT OR REPLACE INTO narratives (
                            week_start, rank, theme, summary,
                            protocols_mentioned, evidence_mention_ids,
                            model_used
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            n.week_start.isoformat(),
                            n.rank,
                            n.theme,
                            n.summary,
                            json.dumps(n.protocols_mentioned),
                            json.dumps(n.evidence_mention_ids),
                            n.model_used,
                        ),
                    )
                    persisted.append(n)
                except Exception as exc:
                    logger.debug("SQLite persist skipped for narrative: %s", exc)
        except Exception as exc:
            logger.warning("Failed to persist narrative rank=%d: %s", n.rank, exc)

    try:
        if hasattr(conn_or_writer, "commit"):
            conn_or_writer.commit()
    except Exception:  # noqa: S110 — commit is best-effort
        pass

    logger.info("Persisted %d narratives for week %s",
                len(persisted), week_start.isoformat())
    return persisted
