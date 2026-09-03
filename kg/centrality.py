"""Centrality scoring engine (Phase 4 of the KAQG pipeline).

Combines the Python-side orchestration logic with the Rust PageRank
binary.  The pipeline:

  1. Fetches degree-centrality raw scores from Neo4j via the query module.
  2. Pulls the (concept, hierarchy, textual) edge projection from Neo4j.
  3. Invokes the PageRank binary to obtain raw PageRank scores per node id.
  4. Fuses degree + PageRank into a single centrality score per concept.
  5. Normalises the scores into the IRT difficulty range [0.1, 1.0].
  6. Persists ``centrality`` and ``difficulty`` properties back to Neo4j.
"""
from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass
from typing import Iterable

from kg import queries
from kg.neo4j_client import open_session, run_query

RUST_BINARY = os.getenv(
    "PAGERANK_BINARY",
    "./rust_kg_engine/target/release/pagerank",
)

# Difficulty floor/ceiling chosen to match the KAQG paper specification.
MIN_DIFFICULTY = 0.1
MAX_DIFFICULTY = 1.0


@dataclass
class ConceptScore:
    name: str
    raw_score: float
    centrality: float
    difficulty: float

    def as_upsert_row(self) -> dict:
        return {
            "concept": self.name,
            "centrality": self.centrality,
            "difficulty": self.difficulty,
        }


def _degree_scores(session) -> dict[str, int]:
    rows = run_query(session, queries.DEGREE_CENTRALITY_QUERY)
    return {row["concept"]: int(row["degree"] or 0) for row in rows}


def _edge_projection(session) -> list[dict]:
    return run_query(session, queries.PAGERANK_PROJECT_QUERY)


def _invoke_pagerank(edges: Iterable[dict]) -> dict[int, float]:
    payload = {"edges": [{"src": r["src"], "dst": r["dst"]} for r in edges]}
    proc = subprocess.run(
        [RUST_BINARY],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"pagerank binary failed: {proc.stderr}")
    if not proc.stdout.strip():
        return {}
    parsed = json.loads(proc.stdout)
    return {int(r["id"]): float(r["score"]) for r in parsed.get("ranks", [])}


def _node_id_lookup(session) -> dict[str, int]:
    rows = run_query(session, "MATCH (c:concept) RETURN c.name AS name, id(c) AS id")
    return {r["name"]: int(r["id"]) for r in rows}


def _normalise(scores: list[float]) -> list[float]:
    """Linear min-max normalise into [MIN_DIFFICULTY, MAX_DIFFICULTY]."""
    if not scores:
        return []
    lo, hi = min(scores), max(scores)
    span = hi - lo
    if span == 0:
        # All concepts are equally central; pick the midpoint difficulty.
        mid = (MIN_DIFFICULTY + MAX_DIFFICULTY) / 2.0
        return [mid for _ in scores]
    scaled = [MIN_DIFFICULTY + (s - lo) * (MAX_DIFFICULTY - MIN_DIFFICULTY) / span for s in scores]
    # Guard against floating-point drift past the inclusive upper bound.
    return [min(MAX_DIFFICULTY, max(MIN_DIFFICULTY, x)) for x in scaled]


def compute_scores(session) -> list[ConceptScore]:
    """Compute centrality + difficulty for every concept node."""
    degrees = _degree_scores(session)
    id_lookup = _node_id_lookup(session)
    edge_rows = _edge_projection(session)
    pagerank_scores = _invoke_pagerank(edge_rows)

    raw_scores: list[float] = []
    concept_order: list[str] = []
    for concept, deg in degrees.items():
        node_id = id_lookup.get(concept)
        pr = pagerank_scores.get(node_id, 0.0) if node_id is not None else 0.0
        # Weighted fusion: degree captures immediate density, PageRank
        # captures structural importance in the whole graph.
        raw = deg + 10.0 * pr
        raw_scores.append(raw)
        concept_order.append(concept)

    normalised = _normalise(raw_scores)
    return [
        ConceptScore(
            name=concept,
            raw_score=raw,
            centrality=raw,
            difficulty=difficulty,
        )
        for concept, raw, difficulty in zip(concept_order, raw_scores, normalised)
    ]


def persist_scores(session, scores: list[ConceptScore]) -> int:
    if not scores:
        return 0
    rows = [s.as_upsert_row() for s in scores]
    result = run_query(session, queries.UPSERT_DIFFICULTY_QUERY, rows=rows)
    if not result:
        return 0
    return int(result[0].get("updated", 0))


def run_scoring_pipeline() -> int:
    """End-to-end Phase 4 entrypoint. Returns the number of nodes updated."""
    with open_session() as session:
        scores = compute_scores(session)
        return persist_scores(session, scores)


if __name__ == "__main__":
    updated = run_scoring_pipeline()
    print(f"[centrality] Updated {updated} concept nodes with difficulty scores.")