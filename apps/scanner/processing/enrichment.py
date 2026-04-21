"""Cross-reference linking and content enrichment."""

import re
from typing import Optional


def link_mention_to_project(conn, mention: dict) -> Optional[int]:
    """Try to find a matching project for a social mention.

    Checks protocol names stored in the projects table against the
    mention's title and content fields.

    Returns:
        The project ID if a match is found, otherwise None.
    """
    title = (mention.get("title") or "").lower()
    content = (mention.get("content") or mention.get("content_snippet") or "").lower()
    combined = f"{title} {content}"

    if not combined.strip():
        return None

    cursor = conn.execute("SELECT id, name FROM projects")
    projects = cursor.fetchall()

    for project_id, project_name in projects:
        if project_name and project_name.lower() in combined:
            return project_id

    # Also check slug and defillama_slug as alternative names
    cursor = conn.execute("SELECT id, slug, defillama_slug FROM projects")
    rows = cursor.fetchall()
    for row_id, slug, dl_slug in rows:
        if slug and slug.lower() in combined:
            return row_id
        if dl_slug and dl_slug.lower() in combined:
            return row_id

    return None


def extract_funding_info(text: str) -> Optional[dict]:
    """Extract funding details from article text using regex.

    Looks for:
    - Funding amount: patterns like $5M, $10 million, $2.5m
    - Round type: seed, series A, series B, pre-seed, etc.
    - Investor names: "led by X", "backed by X", "investors include X"

    Returns:
        Dict with keys 'amount', 'round_type', 'investors' or None if
        no funding info is found.
    """
    if not text:
        return None

    text_str = text

    # Extract funding amount
    amount = None
    amount_patterns = [
        r"\$(\d+(?:\.\d+)?)\s*(?:million|mil|m)\b",
        r"\$(\d+(?:\.\d+)?)\s*(?:billion|bil|b)\b",
        r"raised\s+\$(\d+(?:\.\d+)?)\s*[mbMB]",
        r"\$(\d+(?:\.\d+)?)\s*[MB]\b",
    ]
    for pattern in amount_patterns:
        match = re.search(pattern, text_str, re.IGNORECASE)
        if match:
            raw = match.group(0)
            num = float(match.group(1))
            if re.search(r"[bB](?:illion)?", raw):
                amount = f"${num}B"
            else:
                amount = f"${num}M"
            break

    # Extract round type
    round_type = None
    round_patterns = [
        r"(pre[- ]?seed)\s+(?:round|funding)?",
        r"(seed)\s+(?:round|funding)?",
        r"(series\s+[a-d])\s*(?:round|funding)?",
        r"(strategic)\s+(?:round|funding|investment)",
        r"(private)\s+(?:round|sale)",
    ]
    for pattern in round_patterns:
        match = re.search(pattern, text_str, re.IGNORECASE)
        if match:
            round_type = match.group(1).strip().title()
            break

    # Extract investor names
    investors = []
    investor_patterns = [
        r"(?:led|headed)\s+by\s+([A-Z][\w\s&,]+?)(?:\.|,\s*(?:with|and)\b|\s+(?:participated|joined))",
        r"(?:backed|funded)\s+by\s+([A-Z][\w\s&,]+?)(?:\.|$)",
        r"investors?\s+(?:include|including)\s+([A-Z][\w\s&,]+?)(?:\.|$)",
    ]
    for pattern in investor_patterns:
        match = re.search(pattern, text_str)
        if match:
            raw_investors = match.group(1).strip()
            # Split on comma or " and "
            parts = re.split(r",\s*|\s+and\s+", raw_investors)
            investors.extend([inv.strip() for inv in parts if inv.strip()])
            break

    if not amount and not round_type and not investors:
        return None

    return {
        "amount": amount,
        "round_type": round_type,
        "investors": investors if investors else None,
    }


def link_person_to_project(conn, person_name: str) -> Optional[int]:
    """Try to match a person to a known project.

    Checks the people table for matching names and returns the
    associated project ID.

    Returns:
        The project ID if found, otherwise None.
    """
    if not person_name:
        return None

    name_lower = person_name.lower().strip()

    # Exact match in people table
    try:
        cursor = conn.execute(
            "SELECT project_id FROM people WHERE LOWER(name) = ? LIMIT 1",
            (name_lower,),
        )
        row = cursor.fetchone()
        if row:
            return row[0]
    except Exception:
        pass

    # Partial match fallback in people table
    try:
        cursor = conn.execute(
            "SELECT project_id FROM people WHERE LOWER(name) LIKE ? LIMIT 1",
            (f"%{name_lower}%",),
        )
        row = cursor.fetchone()
        if row:
            return row[0]
    except Exception:
        pass

    return None
