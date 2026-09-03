"""Centrality scoring engine (Phase 4 of the KAQG pipeline).

Implements the IRT difficulty mapping from the KAQG spec:

    b_i = 0.1 + (deg_i - min_deg) / (max_deg - min_deg) * 0.9

so the resulting difficulty coefficient `c.difficulty` lives in [0.1, 1.0].

PageRank from the Rust micro-service is computed in parallel and persisted as
a secondary `c.centrality` enrichment signal that downstream consumers (e.g.
the Phase 5 sampler) can use to rank candidates.  The IRT formula itself is
degree-only as specified.

Pipeline:
  1. Fetch degree per concept from Neo4j.
  2. Compute min/max degree bounds from Neo4j.
  3. Project (concept, hierarchy, textual) edges for PageRank.
  4. Invoke Rust PageRank binary.
  5. Map degree to IRT b using min-max normalisation.
  6. Batch-write `degree`, `centrality`, `difficulty` back to Neo4j.
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

# Difficulty floor/ceiling chosen to match the KAQG paper specification
# and the explicit formula in spec/TASKS.md (4.3).
MIN_DIFFICULTY = 0.1
MAX_DIFFICULTY = 1.0


@dataclass
class ConceptScore:
    name: str
    degree: int
    raw_centrality: float
    centrality: float
    difficulty: float

    def as_upsert_row(self) -> dict:
        return {
            "concept": self.name,
            "degree": self.degree,
            "centrality": self.centrality,
            "difficulty": self.difficulty,
        }


def _degree_scores(session) -> dict[str, int]:
    rows = run_query(session, queries.DEGREE_CENTRALITY_QUERY)
    return {row["concept"]: int(row["degree"] or 0) for row in rows}


def _degree_bounds(session) -> tuple[int, int]:
    rows = run_query(session, queries.DEGREE_BOUNDS_QUERY)
    if not rows:
        return 0, 0
    row = rows[0]
    return int(row["min_deg"] or 0), int(row["max_deg"] or 0)


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


def _irt_difficulty(degree: int, min_deg: int, max_deg: int) -> float:
    """Spec 4.3: b = 0.1 + (deg - min) / (max - min) * 0.9, clamped to [0.1, 1.0]."""
    if max_deg == min_deg:
        return (MIN_DIFFICULTY + MAX_DIFFICULTY) / 2.0
    raw = MIN_DIFFICULTY + (degree - min_deg) * (MAX_DIFFICULTY - MIN_DIFFICULTY) / (max_deg - min_deg)
    return min(MAX_DIFFICULTY, max(MIN_DIFFICULTY, raw))


def _fuse_centrality(degree: int, pagerank: float) -> float:
    """Optional secondary score: degree + scaled PageRank, kept for ranking."""
    return float(degree) + 10.0 * pagerank


def compute_scores(session) -> list[ConceptScore]:
    """Compute degree, IRT difficulty, and auxiliary centrality per concept."""
    degrees = _degree_scores(session)
    min_deg, max_deg = _degree_bounds(session)
    id_lookup = _node_id_lookup(session)
    edge_rows = _edge_projection(session)
    pagerank_scores = _invoke_pagerank(edge_rows)

    out: list[ConceptScore] = []
    for concept, deg in degrees.items():
        node_id = id_lookup.get(concept)
        pr = pagerank_scores.get(node_id, 0.0) if node_id is not None else 0.0
        difficulty = _irt_difficulty(deg, min_deg, max_deg)
        out.append(
            ConceptScore(
                name=concept,
                degree=deg,
                raw_centrality=pr,
                centrality=_fuse_centrality(deg, pr),
                difficulty=difficulty,
            )
        )
    return out


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