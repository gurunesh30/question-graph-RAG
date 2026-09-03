"""Export helpers — JSON and Markdown writers for a ``QuestionBank``."""
from __future__ import annotations

from pathlib import Path
from typing import IO

from kaqg.domain.models import QuestionBank


def write_json(bank: QuestionBank, path: str | Path) -> Path:
    out = Path(path)
    out.write_text(bank.to_json(indent=2), encoding="utf-8")
    return out


def write_markdown(bank: QuestionBank, path: str | Path) -> Path:
    out = Path(path)
    lines: list[str] = [
        f"# Question Bank — difficulty: {bank.difficulty}",
        f"_Mode: {bank.mode} • {len(bank.questions)} questions_",
        "",
    ]
    for i, q in enumerate(bank.questions, 1):
        lines.append(f"## {i}. {q.question}")
        for label, option in q.options.items():
            marker = " **(correct)**" if label == q.correct_answer else ""
            lines.append(f"- **{label}.** {option}{marker}")
        lines.append("")
        lines.append(f"_Explanation:_ {q.explanation}")
        lines.append("")
    out.write_text("\n".join(lines), encoding="utf-8")
    return out


def write_auto(bank: QuestionBank, path: str | Path) -> Path:
    """Pick JSON or Markdown based on file extension."""
    p = Path(path)
    if p.suffix.lower() in {".md", ".markdown"}:
        return write_markdown(bank, p)
    return write_json(bank, p)
