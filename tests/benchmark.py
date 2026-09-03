"""Smoke benchmark that exercises the scoring and generation code paths
against an in-memory mock graph.  Useful for verifying the wiring of the
pipeline without a live Neo4j instance.
"""
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from kg.centrality import _irt_difficulty
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
    # Use the spec IRT formula: b = 0.1 + (deg - min)/(max - min) * 0.9
    # We feed the subgraphs' difficulty as a stand-in for degree here.
    raw_degrees = [int(round(s.centrality * 10)) for s in subgraphs]
    min_d, max_d = min(raw_degrees), max(raw_degrees)
    difficulties = [_irt_difficulty(d, min_d, max_d) for d in raw_degrees]
    assert min(difficulties) >= 0.1 and max(difficulties) <= 1.0

    zipped = list(zip(subgraphs, difficulties))
    for band, (lo, hi) in DIFFICULTY_BANDS.items():
        picked = [s for s, d in zipped if lo <= d < hi][:3]
        for sg in picked:
            mcq = _mock_question(sg, band)
            assert mcq.correct_answer in mcq.options
    elapsed = time.perf_counter() - start
    print(f"[bench] {len(subgraphs)} subgraphs scored + 9 mock questions in {elapsed:.3f}s")


if __name__ == "__main__":
    main()