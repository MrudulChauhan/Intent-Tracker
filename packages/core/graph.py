"""Graph helpers for the entities/relationships tables (migration 004).

These wrap the Writer adapter (SupabaseWriter in prod) so scanners and batch
jobs can populate the relationship graph without knowing about PostgREST.

The SQLite path is not implemented here — the local dev DB does not have the
entities/relationships tables. Call these through a SupabaseWriter (which is
what CI + Vercel use).
"""

from __future__ import annotations

import logging
from typing import Any, Iterable, Optional, TypedDict

from core.supabase_writer import SupabaseWriter


logger = logging.getLogger(__name__)


class GraphNode(TypedDict, total=False):
    id: int
    entity_type: str
    external_id: Optional[int]
    name: str
    slug: Optional[str]
    metadata: Optional[dict[str, Any]]


class GraphEdge(TypedDict, total=False):
    id: int
    from_id: int
    to_id: int
    relationship_type: str
    source_url: Optional[str]
    confidence: float


class Neighborhood(TypedDict):
    nodes: list[GraphNode]
    edges: list[GraphEdge]


VALID_ENTITY_TYPES: tuple[str, ...] = (
    "project", "investor", "person", "integration",
)

VALID_RELATIONSHIP_TYPES: tuple[str, ...] = (
    "invested_in", "integrates_with", "founded_by",
    "acquired", "partnered_with", "uses_solver",
)


def upsert_entity(
    writer: SupabaseWriter,
    entity_type: str,
    name: str,
    external_id: Optional[int] = None,
    metadata: Optional[dict[str, Any]] = None,
) -> Optional[int]:
    """Insert or update a node in the `entities` table. Returns the entity id.

    Uniqueness is on (entity_type, name) — re-calling with the same pair
    returns the existing id.
    """
    if entity_type not in VALID_ENTITY_TYPES:
        raise ValueError(f"invalid entity_type: {entity_type!r}")
    name = name.strip()
    if not name:
        raise ValueError("entity name must be non-empty")

    row: dict[str, Any] = {"entity_type": entity_type, "name": name}
    if external_id is not None:
        row["external_id"] = external_id
    if metadata is not None:
        row["metadata"] = metadata
    return writer.upsert_entity(row)


def add_relationship(
    writer: SupabaseWriter,
    from_id: int,
    to_id: int,
    relationship_type: str,
    source_url: Optional[str] = None,
    confidence: float = 1.0,
) -> Optional[int]:
    """Insert a directed edge. No-op if (from_id,to_id,relationship_type) exists."""
    if relationship_type not in VALID_RELATIONSHIP_TYPES:
        raise ValueError(f"invalid relationship_type: {relationship_type!r}")
    if not 0.0 <= confidence <= 1.0:
        raise ValueError(f"confidence must be between 0 and 1, got {confidence}")

    row: dict[str, Any] = {
        "from_id": int(from_id),
        "to_id": int(to_id),
        "relationship_type": relationship_type,
        "confidence": float(confidence),
    }
    if source_url is not None:
        row["source_url"] = source_url
    return writer.insert_relationship(row)


def get_neighbors(
    writer: SupabaseWriter,
    entity_id: int,
    depth: int = 1,
) -> Neighborhood:
    """Return the 1- or 2-hop neighborhood around `entity_id`.

    Output shape matches the /graph page: { "nodes": [...], "edges": [...] }
    with de-duplicated nodes keyed by entity id.
    """
    if depth not in (1, 2):
        raise ValueError("depth must be 1 or 2")

    frontier: set[int] = {int(entity_id)}
    visited: set[int] = set()
    all_edges: list[GraphEdge] = []
    seen_edge_ids: set[int] = set()

    for _ in range(depth):
        new_edges = writer.fetch_edges_for_entities(frontier)
        next_frontier: set[int] = set()
        for e in new_edges:
            if e.get("id") in seen_edge_ids:
                continue
            seen_edge_ids.add(e["id"])
            all_edges.append(e)  # type: ignore[arg-type]
            for side in ("from_id", "to_id"):
                nid = e.get(side)
                if isinstance(nid, int) and nid not in visited and nid not in frontier:
                    next_frontier.add(nid)
        visited |= frontier
        frontier = next_frontier
        if not frontier:
            break
    visited |= frontier

    nodes = writer.fetch_entities_by_ids(visited) if visited else []
    return {"nodes": list(nodes), "edges": all_edges}


def bulk_add_relationships(
    writer: SupabaseWriter,
    edges: Iterable[dict[str, Any]],
) -> int:
    """Add many edges. Returns count of edges that were actually inserted."""
    inserted = 0
    for e in edges:
        res = add_relationship(
            writer,
            from_id=e["from_id"],
            to_id=e["to_id"],
            relationship_type=e["relationship_type"],
            source_url=e.get("source_url"),
            confidence=float(e.get("confidence", 1.0)),
        )
        if res:
            inserted += 1
    return inserted
