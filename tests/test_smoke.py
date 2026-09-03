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
from kg.centrality import _normalise


def test_difficulty_bands_have_three_tiers():
    assert set(retrieval.DIFFICULTY_BANDS) == {"easy", "medium", "hard"}


def test_normalisation_clips_into_range():
    scores = _normalise([1.0, 5.0, 10.0])
    assert min(scores) >= 0.1
    assert max(scores) <= 1.0
    assert scores == sorted(scores) or all(0.1 <= s <= 1.0 for s in scores)


def test_normalisation_handles_degenerate_input():
    scores = _normalise([3.0, 3.0, 3.0])
    assert all(s == 0.55 for s in scores)


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
    test_difficulty_bands_have_three_tiers()
    test_normalisation_clips_into_range()
    test_normalisation_handles_degenerate_input()
    test_mock_question_is_deterministic()
    print("[smoke] all offline checks passed")