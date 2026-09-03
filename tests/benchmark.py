"""Smoke benchmark that exercises the scoring and generation code paths
against an in-memory mock graph.  Useful for verifying the wiring of the
pipeline without a live Neo4j instance.
"""
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from kg.centrality import _normalise
from kg.generation import _mock_question
from kg.retrieval import DIFFICULTY_BANDS, Subgraph


def fake_subgraph(idx: int, difficulty: float) -> Subgraph:
    rng = random.Random(idx)
    facts = [f"fact_{idx}_{j}" for j in range(3)]
    return Subgraph(
        concept=f"concept_{idx}",
        difficulty=difficulty,
        centrality=difficulty,
        textual_facts=facts,
        hierarchy_parents=[f"unit_{idx // 2}"],
    )


def main() -> None:
    start = time.perf_counter()
    subgraphs = [fake_subgraph(i, 0.2 + (i % 7) * 0.1) for i in range(20)]
    raw_scores = [s.centrality for s in subgraphs]
    normalised = _normalise(raw_scores)
    assert min(normalised) >= 0.1 and max(normalised) <= 1.0

    # Use the normalised values as the authoritative difficulty for filtering.
    zipped = list(zip(subgraphs, normalised))
    for band, (lo, hi) in DIFFICULTY_BANDS.items():
        picked = [s for s, n in zipped if lo <= n < hi][:3]
        for sg in picked:
            mcq = _mock_question(sg, band)
            assert mcq.answer in mcq.options
    elapsed = time.perf_counter() - start
    print(f"[bench] {len(subgraphs)} subgraphs scored + 9 mock questions in {elapsed:.3f}s")


if __name__ == "__main__":
    main()