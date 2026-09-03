"""Domain-level unit tests (pure, no I/O)."""
from __future__ import annotations

import pytest

from kaqg.domain import (
    DIFFICULTY_BANDS,
    KnowledgeGraph,
    MCQ,
    OPTION_LABELS,
    QuestionBank,
    Subgraph,
    Triple,
    ConceptScore,
    IRTDifficulty,
    fuse_centrality,
    irt_difficulty,
)
from kaqg.errors import ValidationError


# ---- IRT math ----


def test_irt_difficulty_matches_spec_formula():
    assert irt_difficulty(0, 0, 10) == pytest.approx(0.1)
    assert irt_difficulty(5, 0, 10) == pytest.approx(0.55)
    assert irt_difficulty(10, 0, 10) == pytest.approx(1.0)


def test_irt_difficulty_handles_degenerate_input():
    assert irt_difficulty(7, 7, 7) == pytest.approx(0.55)


def test_irt_difficulty_clamps_outliers():
    assert irt_difficulty(-5, 0, 10) == pytest.approx(0.1)
    assert irt_difficulty(99, 0, 10) == pytest.approx(1.0)


def test_fuse_centrality_combines_signals():
    assert fuse_centrality(2, 0.1, weight=10.0) == pytest.approx(3.0)


def test_irt_difficulty_class_rejects_invalid_bounds():
    with pytest.raises(ValidationError):
        IRTDifficulty(min_difficulty=0.9, max_difficulty=0.1)
    valid = IRTDifficulty(min_difficulty=0.2, max_difficulty=0.8)
    assert valid.compute(5, 0, 10) == pytest.approx(0.5)


# ---- Triple validation ----


def test_triple_validates_relationship_against_node_types():
    with pytest.raises(ValidationError):
        Triple("PCB", "textual", "part_of", "Unit 1", "hierarchy")
    with pytest.raises(ValidationError):
        Triple("Unit 1", "hierarchy", "include_in", "PCB", "textual")
    with pytest.raises(ValidationError):
        Triple("PCB", "textual", "is_a", "Unit 1", "hierarchy")
    # A correct triple is accepted.
    Triple("PCB", "textual", "is_a", "Process Management", "concept")


def test_triple_rejects_empty_strings():
    with pytest.raises(ValidationError):
        Triple("", "concept", "is_a", "x", "textual")


def test_knowledge_graph_from_payload_roundtrip():
    payload = {
        "triples": [
            {"head": "PCB", "head_type": "textual", "relation": "is_a",
             "tail": "Process Management", "tail_type": "concept"},
        ]
    }
    kg = KnowledgeGraph.from_payload(payload)
    assert len(kg.triples) == 1
    assert kg.to_payload() == payload


def test_knowledge_graph_rejects_empty():
    with pytest.raises(ValidationError):
        KnowledgeGraph(triples=())


# ---- MCQ validation ----


def _valid_mcq() -> MCQ:
    return MCQ(
        concept="Process Management",
        difficulty="medium",
        question="What is the role of the PCB?",
        options={"A": "X", "B": "Y", "C": "Z", "D": "W"},
        correct_answer="A",
        explanation="It tracks process state.",
    )


def test_mcq_serialisation_uses_correct_answer_key():
    payload = _valid_mcq().to_dict()
    assert "correct_answer" in payload
    assert "answer" not in payload
    assert set(payload["options"].keys()) == set(OPTION_LABELS)


def test_mcq_rejects_missing_or_wrong_options():
    base = _valid_mcq()
    with pytest.raises(ValidationError):
        MCQ(**{**base.to_dict(), "options": {"A": "x", "B": "y", "C": "z"}})


def test_mcq_rejects_invalid_correct_answer():
    base = _valid_mcq()
    with pytest.raises(ValidationError):
        MCQ(**{**base.to_dict(), "correct_answer": "Z"})


# ---- Subgraph ----


def test_subgraph_context_block_includes_hierarchy_and_facts():
    sg = Subgraph(
        concept="PCB",
        difficulty=0.3,
        centrality=0.5,
        textual_facts=["state", "scheduling"],
        hierarchy_parents=["Unit 1"],
    )
    block = sg.context_block()
    assert "PCB" in block
    assert "Unit 1" in block
    assert "state" in block


# ---- QuestionBank ----


def test_question_bank_round_trip():
    bank = QuestionBank(
        difficulty="easy",
        questions=(_valid_mcq(),),
        mode="mock",
    )
    payload = bank.to_dict()
    assert payload["count"] == 1
    assert payload["mode"] == "mock"
    assert payload["questions"][0]["correct_answer"] == "A"


# ---- ConceptScore ----


def test_concept_score_validates_bounds():
    base = dict(name="x", degree=1, centrality=1.0, difficulty=0.5)
    ConceptScore(**base)  # ok
    with pytest.raises(ValidationError):
        ConceptScore(**{**base, "difficulty": 1.5})
    with pytest.raises(ValidationError):
        ConceptScore(**{**base, "degree": -1})


# ---- Difficulty bands constant ----


def test_difficulty_bands_keys():
    assert set(DIFFICULTY_BANDS) == {"easy", "medium", "hard"}
