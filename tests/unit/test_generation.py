"""Unit tests for the generation mock + prompt builder."""
from __future__ import annotations

from kaqg.domain import Subgraph
from kaqg.pipelines.generation import (
    _build_prompt,
    _mock_question,
    _parse_response,
)
from kaqg.errors import ValidationError


def _sg() -> Subgraph:
    return Subgraph(
        concept="Deadlock",
        difficulty=0.5,
        centrality=0.3,
        textual_facts=["Hold and Wait", "Circular Wait", "Mutual Exclusion"],
        hierarchy_parents=["Unit 2"],
    )


def test_build_prompt_includes_context():
    prompt = _build_prompt(_sg(), "medium")
    assert "Deadlock" in prompt
    assert "Unit 2" in prompt
    assert "Hold and Wait" in prompt
    assert "correct_answer" in prompt


def test_mock_question_is_deterministic():
    sg = _sg()
    q1 = _mock_question(sg, "easy")
    q2 = _mock_question(sg, "easy")
    assert q1.question == q2.question
    assert q1.correct_answer == q2.correct_answer
    assert set(q1.options) == {"A", "B", "C", "D"}


def test_parse_response_accepts_legacy_answer_key():
    sg = _sg()
    parsed = _parse_response(
        {
            "question": "Q?",
            "options": {"A": "x", "B": "y", "C": "z", "D": "w"},
            "answer": "B",
            "explanation": "Because.",
        },
        sg,
        "medium",
    )
    assert parsed.correct_answer == "B"


def test_parse_response_falls_back_when_answer_missing():
    sg = _sg()
    parsed = _parse_response(
        {
            "question": "Q?",
            "options": {"A": "x", "B": "y", "C": "z", "D": "w"},
            "explanation": "Because.",
        },
        sg,
        "medium",
    )
    assert parsed.correct_answer == "A"
