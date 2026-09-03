"""Offline smoke tests for the KAQG Python pipeline.

Run with: ``python -m pytest tests/`` (or ``python tests/test_smoke.py``).
These tests intentionally avoid Neo4j so they can run in CI without the
cloud database being reachable.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from kg import retrieval
from kg.generation import _mock_question, generate_batch
from kg.centrality import _irt_difficulty


def test_irt_difficulty_matches_spec_formula():
    # b = 0.1 + (deg - min)/(max - min) * 0.9
    #   deg=0 -> 0.1
    #   deg=5, min=0, max=10 -> 0.1 + 0.5*0.9 = 0.55
    #   deg=10 -> 1.0
    assert _irt_difficulty(0, 0, 10) == 0.1
    assert _irt_difficulty(5, 0, 10) == 0.55
    assert _irt_difficulty(10, 0, 10) == 1.0


def test_irt_difficulty_handles_degenerate_input():
    # All degrees equal -> midpoint of [0.1, 1.0].
    assert _irt_difficulty(7, 7, 7) == 0.55


def test_irt_difficulty_clamps_outliers():
    # A degree below the min should still hit the floor.
    assert _irt_difficulty(-1, 0, 10) == 0.1
    # A degree above the max should still hit the ceiling.
    assert _irt_difficulty(99, 0, 10) == 1.0


def test_difficulty_bands_have_three_tiers():
    assert set(retrieval.DIFFICULTY_BANDS) == {"easy", "medium", "hard"}


def test_mock_question_is_deterministic():
    sg = retrieval.Subgraph(
        concept="Process Management",
        difficulty=0.5,
        centrality=0.8,
        textual_facts=["PCB", "Context Switch", "Scheduler"],
        hierarchy_parents=["Unit 1"],
    )
    q1 = _mock_question(sg, "medium")
    q2 = _mock_question(sg, "medium")
    assert q1.question == q2.question
    assert q1.answer == q2.answer
    assert set(q1.options.keys()) == {"A", "B", "C", "D"}


def test_generate_batch_uses_mock_when_no_key(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    sg = retrieval.Subgraph(
        concept="Deadlock",
        difficulty=0.6,
        centrality=0.4,
        textual_facts=["Hold and Wait", "Circular Wait"],
        hierarchy_parents=["Unit 3"],
    )
    out = generate_batch([sg], "medium")
    assert len(out) == 1
    assert out[0].concept == "Deadlock"


if __name__ == "__main__":
    test_irt_difficulty_matches_spec_formula()
    test_irt_difficulty_handles_degenerate_input()
    test_irt_difficulty_clamps_outliers()
    test_difficulty_bands_have_three_tiers()
    test_mock_question_is_deterministic()
    print("[smoke] all offline checks passed")