"""Domain models for the KAQG pipeline.

Pure data containers — no I/O, no global state.  Every model validates
its own invariants in ``__post_init__`` so bad data is caught at the
boundary instead of deep inside a pipeline.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any

from kaqg.errors import ValidationError

VALID_NODE_TYPES: frozenset[str] = frozenset({"hierarchy", "concept", "textual"})
VALID_RELATIONS: frozenset[str] = frozenset({"part_of", "include_in", "is_a"})
DIFFICULTY_BANDS: tuple[str, ...] = ("easy", "medium", "hard")
OPTION_LABELS: tuple[str, ...] = ("A", "B", "C", "D")


# ---------------------------------------------------------------------------
# Ingestion
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Triple:
    head: str
    head_type: str
    relation: str
    tail: str
    tail_type: str

    def __post_init__(self) -> None:
        for field_name, value in (
            ("head", self.head),
            ("tail", self.tail),
            ("head_type", self.head_type),
            ("tail_type", self.tail_type),
            ("relation", self.relation),
        ):
            if not isinstance(value, str) or not value.strip():
                raise ValidationError(f"Triple.{field_name} must be a non-empty string")
        if self.head_type not in VALID_NODE_TYPES:
            raise ValidationError(
                f"Invalid head_type '{self.head_type}'. "
                f"Expected one of {sorted(VALID_NODE_TYPES)}"
            )
        if self.tail_type not in VALID_NODE_TYPES:
            raise ValidationError(
                f"Invalid tail_type '{self.tail_type}'. "
                f"Expected one of {sorted(VALID_NODE_TYPES)}"
            )
        rel = self.relation.lower()
        if rel not in VALID_RELATIONS:
            raise ValidationError(
                f"Invalid relation '{self.relation}'. "
                f"Expected one of {sorted(VALID_RELATIONS)}"
            )
        if rel == "part_of" and not (self.head_type == "hierarchy" and self.tail_type == "hierarchy"):
            raise ValidationError("PART_OF requires both endpoints to be hierarchy nodes")
        if rel == "include_in" and not (self.head_type == "concept" and self.tail_type == "hierarchy"):
            raise ValidationError("INCLUDE_IN must be (concept -> hierarchy)")
        if rel == "is_a" and not (self.head_type == "textual" and self.tail_type == "concept"):
            raise ValidationError("IS_A must be (textual -> concept)")

    @property
    def relation_upper(self) -> str:
        return self.relation.upper()

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class KnowledgeGraph:
    triples: tuple[Triple, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.triples, tuple):
            object.__setattr__(self, "triples", tuple(self.triples))
        if not self.triples:
            raise ValidationError("KnowledgeGraph must contain at least one Triple")

    def to_payload(self) -> dict[str, list[dict[str, str]]]:
        return {"triples": [t.to_dict() for t in self.triples]}

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "KnowledgeGraph":
        raw = payload.get("triples")
        if not isinstance(raw, list):
            raise ValidationError("LLM payload missing 'triples' list")
        triples = []
        for idx, item in enumerate(raw):
            try:
                triples.append(
                    Triple(
                        head=item["head"],
                        head_type=item["head_type"],
                        relation=item["relation"],
                        tail=item["tail"],
                        tail_type=item["tail_type"],
                    )
                )
            except (KeyError, TypeError) as exc:
                raise ValidationError(f"Triple #{idx} is malformed: {exc}") from exc
        return cls(triples=triples)


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ConceptScore:
    name: str
    degree: int
    centrality: float
    difficulty: float

    def __post_init__(self) -> None:
        if not self.name:
            raise ValidationError("ConceptScore.name must be non-empty")
        if self.degree < 0:
            raise ValidationError("ConceptScore.degree must be >= 0")
        if not (0.0 <= self.difficulty <= 1.0):
            raise ValidationError(
                f"ConceptScore.difficulty {self.difficulty} outside [0, 1]"
            )

    def to_upsert_row(self) -> dict[str, Any]:
        return {
            "concept": self.name,
            "degree": self.degree,
            "centrality": self.centrality,
            "difficulty": self.difficulty,
        }


# ---------------------------------------------------------------------------
# Retrieval
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class Subgraph:
    concept: str
    difficulty: float
    centrality: float
    textual_facts: list[str] = field(default_factory=list)
    hierarchy_parents: list[str] = field(default_factory=list)

    def context_block(self) -> str:
        parents = ", ".join(self.hierarchy_parents) or "(no parent hierarchy)"
        facts = "\n    - ".join(self.textual_facts) or "(no textual facts)"
        return (
            f"Concept: {self.concept}\n"
            f"Parent hierarchy: {parents}\n"
            f"Associated facts:\n    - {facts}"
        )


# ---------------------------------------------------------------------------
# Generation
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class MCQ:
    concept: str
    difficulty: str
    question: str
    options: dict[str, str]
    correct_answer: str
    explanation: str

    def __post_init__(self) -> None:
        if not self.question.strip():
            raise ValidationError("MCQ.question must be non-empty")
        if not self.explanation.strip():
            raise ValidationError("MCQ.explanation must be non-empty")
        if self.difficulty not in DIFFICULTY_BANDS:
            raise ValidationError(
                f"MCQ.difficulty '{self.difficulty}' not in {DIFFICULTY_BANDS}"
            )
        if len(self.options) != 4:
            raise ValidationError(
                f"MCQ must have exactly 4 options, got {len(self.options)}"
            )
        for label in OPTION_LABELS:
            if label not in self.options or not str(self.options[label]).strip():
                raise ValidationError(f"MCQ missing or empty option {label}")
        if self.correct_answer not in self.options:
            raise ValidationError(
                f"MCQ.correct_answer '{self.correct_answer}' not in options {list(self.options)}"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "concept": self.concept,
            "difficulty": self.difficulty,
            "question": self.question,
            "options": dict(self.options),
            "correct_answer": self.correct_answer,
            "explanation": self.explanation,
        }


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class QuestionBank:
    difficulty: str
    questions: tuple[MCQ, ...]
    mode: str = "live"
    source_pdf: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "difficulty": self.difficulty,
            "count": len(self.questions),
            "source_pdf": self.source_pdf,
            "questions": [q.to_dict() for q in self.questions],
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)
