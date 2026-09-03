"""Subgraph retrieval sampler for KAQG Phase 5.

Filters concept nodes by IRT difficulty band and pulls a structural
neighborhood (textual facts + parent hierarchies) for each candidate.

Difficulty bands match the thresholds described in TASKS.md 5.2:

  easy    :  b < 0.4
  medium  :  0.4 <= b < 0.7
  hard    :  b >= 0.7
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from kg import queries as queries_mod
from kg.neo4j_client import open_session, run_query

DIFFICULTY_BANDS: dict[str, tuple[float, float]] = {
    "easy": (0.0, 0.4),
    "medium": (0.4, 0.7),
    "hard": (0.7, 1.01),
}


@dataclass
class Subgraph:
    concept: str
    difficulty: float
    centrality: float
    textual_facts: list[str] = field(default_factory=list)
    hierarchy_parents: list[str] = field(default_factory=list)

    def context_block(self) -> str:
        """Render the subgraph as a natural-language context for an LLM."""
        parents = ", ".join(self.hierarchy_parents) or "(no parent hierarchy)"
        facts = "\n    - ".join(self.textual_facts) or "(no textual facts)"
        return (
            f"Concept: {self.concept}\n"
            f"Parent hierarchy: {parents}\n"
            f"Associated facts:\n    - {facts}"
        )


def resolve_band(difficulty: Optional[str]) -> tuple[float, float]:
    key = (difficulty or "medium").lower()
    if key not in DIFFICULTY_BANDS:
        raise ValueError(f"Unknown difficulty '{difficulty}'. "
                         f"Expected one of {list(DIFFICULTY_BANDS)}")
    return DIFFICULTY_BANDS[key]


def sample_concepts(session, difficulty: Optional[str], limit: int) -> list[Subgraph]:
    low, high = resolve_band(difficulty)
    rows = run_query(
        session,
        queries_mod.DIFFICULTY_BAND_QUERY,
        min_b=low,
        max_b=high,
        limit=limit,
    )
    return [
        Subgraph(
            concept=row["concept"],
            difficulty=float(row["difficulty"] or 0.0),
            centrality=float(row["centrality"] or 0.0),
        )
        for row in rows
    ]


def expand_subgraph(session, subgraph: Subgraph) -> Subgraph:
    rows = run_query(
        session,
        queries_mod.SUBGRAPH_EXPANSION_QUERY,
        concept_name=subgraph.concept,
    )
    if not rows:
        return subgraph
    row = rows[0]
    subgraph.textual_facts = [t for t in (row.get("textual_facts") or []) if t]
    subgraph.hierarchy_parents = [h for h in (row.get("hierarchy_parents") or []) if h]
    return subgraph


def fetch_subgraphs(difficulty: Optional[str] = "medium",
                    count: int = 5) -> list[Subgraph]:
    with open_session() as session:
        seeds = sample_concepts(session, difficulty, count)
        return [expand_subgraph(session, s) for s in seeds]


if __name__ == "__main__":
    for sg in fetch_subgraphs("medium", 3):
        print(sg.context_block())
        print("---")