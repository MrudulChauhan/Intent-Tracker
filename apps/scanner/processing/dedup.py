"""Deduplication logic for URLs and titles."""

import re
import string
from urllib.parse import urlparse, urlencode, parse_qs

# Common tracking query parameters to strip
TRACKING_PARAMS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "ref", "fbclid", "gclid", "mc_cid", "mc_eid", "s", "source",
    "si", "t", "feature",
}

# Tables that dedup helpers are allowed to scan. The `table` argument is
# interpolated directly into SQL (sqlite3 doesn't bind identifiers), so we
# validate against this allow-list to prevent SQL injection by refactor.
_DEDUP_URL_TABLES = frozenset({"social_mentions"})
_DEDUP_TITLE_TABLES = frozenset({"social_mentions", "projects"})


def _assert_allowed(table: str, allowed: frozenset[str]) -> None:
    if table not in allowed:
        raise ValueError(
            f"Table {table!r} is not in the dedup allow-list {sorted(allowed)}"
        )


def normalize_url(url: str) -> str:
    """Normalize a URL by stripping tracking params, trailing slashes, and lowering."""
    if not url:
        return ""

    url = url.strip()
    parsed = urlparse(url)

    # Lowercase scheme and host
    scheme = parsed.scheme.lower() or "https"
    netloc = parsed.netloc.lower()

    # Remove www. prefix
    if netloc.startswith("www."):
        netloc = netloc[4:]

    # Strip tracking query params
    query_params = parse_qs(parsed.query, keep_blank_values=False)
    filtered = {k: v for k, v in query_params.items() if k.lower() not in TRACKING_PARAMS}

    # Rebuild query string (sorted for consistency)
    query = urlencode(filtered, doseq=True) if filtered else ""

    # Strip trailing slash from path
    path = parsed.path.rstrip("/")

    # Rebuild
    normalized = f"{scheme}://{netloc}{path}"
    if query:
        normalized += f"?{query}"

    return normalized


def is_duplicate_url(conn, url: str, table: str = "social_mentions") -> bool:
    """Check if a normalized URL already exists in the given table."""
    if not url:
        return False

    _assert_allowed(table, _DEDUP_URL_TABLES)
    normalized = normalize_url(url)
    cursor = conn.execute(
        f"SELECT 1 FROM {table} WHERE url = ? OR url = ? LIMIT 1",
        (url, normalized),
    )
    return cursor.fetchone() is not None


def normalize_title(title: str) -> str:
    """Lowercase and strip punctuation from a title."""
    if not title:
        return ""
    title = title.lower().strip()
    title = title.translate(str.maketrans("", "", string.punctuation))
    # Collapse whitespace
    title = re.sub(r"\s+", " ", title).strip()
    return title


def similarity_score(a: str, b: str) -> float:
    """Compute Jaccard similarity based on word overlap."""
    if not a or not b:
        return 0.0

    words_a = set(normalize_title(a).split())
    words_b = set(normalize_title(b).split())

    if not words_a or not words_b:
        return 0.0

    intersection = words_a & words_b
    union = words_a | words_b

    return len(intersection) / len(union)


def is_duplicate_title(conn, title: str, table: str, threshold: float = 0.8) -> bool:
    """Check if a similar title already exists in the given table.

    Compares the candidate title against all existing titles using
    Jaccard word-overlap similarity.
    """
    if not title:
        return False

    _assert_allowed(table, _DEDUP_TITLE_TABLES)
    cursor = conn.execute(f"SELECT title FROM {table}")
    rows = cursor.fetchall()

    for (existing_title,) in rows:
        if existing_title and similarity_score(title, existing_title) >= threshold:
            return True

    return False
