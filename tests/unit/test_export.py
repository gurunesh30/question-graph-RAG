"""Unit tests for the export module."""
from __future__ import annotations

import json
from pathlib import Path

from kaqg.domain import MCQ, QuestionBank
from kaqg.export import write_auto, write_json, write_markdown


def _bank() -> QuestionBank:
    return QuestionBank(
        difficulty="medium",
        mode="mock",
        questions=(
            MCQ(
                concept="X",
                difficulty="medium",
                question="Why?",
                options={"A": "x", "B": "y", "C": "z", "D": "w"},
                correct_answer="C",
                explanation="Because.",
            ),
        ),
    )


def test_write_json(tmp_path: Path):
    out = write_json(_bank(), tmp_path / "q.json")
    payload = json.loads(out.read_text())
    assert payload["count"] == 1
    assert payload["questions"][0]["correct_answer"] == "C"


def test_write_markdown_marks_correct_option(tmp_path: Path):
    out = write_markdown(_bank(), tmp_path / "q.md")
    text = out.read_text()
    assert "**(correct)**" in text
    assert "Why?" in text


def test_write_auto_picks_format_by_extension(tmp_path: Path):
    md_path = write_auto(_bank(), tmp_path / "q.md")
    assert md_path.read_text().startswith("# Question Bank")
    json_path = write_auto(_bank(), tmp_path / "q.json")
    json.loads(json_path.read_text())
