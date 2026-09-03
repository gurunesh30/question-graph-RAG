"""MCQ generation pipeline (Phase 5, step 2-3).

Builds a graph-conditioned prompt, calls OpenRouter, and validates the
returned MCQ structure.  Falls back to a deterministic mock when no
OpenRouter API key is configured (useful for tests + offline e2e).
"""
from __future__ import annotations

import logging
import random
from dataclasses import dataclass

from kaqg.clients.openrouter import OpenRouterClient
from kaqg.config import Settings, get_settings
from kaqg.domain.models import MCQ, Subgraph
from kaqg.errors import GenerationError

LOGGER = logging.getLogger("kaqg.generation")

DIFFICULTY_PROMPTS: dict[str, str] = {
    "easy": "Write a straightforward recall question with one obviously correct option.",
    "medium": "Write an applied question that requires combining two of the listed facts.",
    "hard": "Write a synthesis question requiring inference across the hierarchy and facts.",
}

SYSTEM_PROMPT = """You are an expert exam setter following the KAQG paper specification.
Generate exactly ONE multiple-choice question from the knowledge subgraph below.

Difficulty directive: {directive}

Knowledge Subgraph:
{context}

Rules:
- Question must be answerable solely from the subgraph above.
- Provide FOUR options labelled A, B, C, D.
- Exactly one option is correct.
- Distractors must be plausible but incorrect given the facts.
- Explanation must justify the correct answer and cite the relevant facts.

Return STRICT JSON in this shape and nothing else:
{{
  "question": "...",
  "options": {{"A": "...", "B": "...", "C": "...", "D": "..."}},
  "correct_answer": "A",
  "explanation": "..."
}}
"""


@dataclass(slots=True)
class GenerationRequest:
    difficulty: str = "medium"
    count: int = 5
    use_mock: bool = False  # force mock even when LLM is configured


class GenerationPipeline:
    """End-to-end MCQ generation for a list of subgraphs."""

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        llm: OpenRouterClient | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._llm = llm or OpenRouterClient(self._settings)
        self._has_api_key = bool(self._settings.openrouter_api_key)

    def close(self) -> None:
        self._llm.close()

    def generate(self, subgraph: Subgraph, request: GenerationRequest) -> MCQ:
        if request.use_mock or not self._has_api_key:
            return _mock_question(subgraph, request.difficulty)
        prompt = _build_prompt(subgraph, request.difficulty)
        try:
            payload = self._llm.complete_json(prompt)
        except Exception as exc:  # noqa: BLE001
            LOGGER.warning("LLM generation failed (%s); falling back to mock", exc)
            return _mock_question(subgraph, request.difficulty)
        return _parse_response(payload, subgraph, request.difficulty)

    def generate_many(
        self, subgraphs: list[Subgraph], request: GenerationRequest
    ) -> list[MCQ]:
        if request.difficulty not in DIFFICULTY_PROMPTS:
            raise GenerationError(
                f"Unknown difficulty '{request.difficulty}'. "
                f"Expected one of {list(DIFFICULTY_PROMPTS)}"
            )
        return [self.generate(sg, request) for sg in subgraphs]

    def __enter__(self) -> "GenerationPipeline":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()


# ---------------------------------------------------------------------------
# Pure helpers (testable)
# ---------------------------------------------------------------------------


def _build_prompt(subgraph: Subgraph, difficulty: str) -> str:
    directive = DIFFICULTY_PROMPTS.get(difficulty, DIFFICULTY_PROMPTS["medium"])
    return SYSTEM_PROMPT.format(directive=directive, context=subgraph.context_block())


def _parse_response(payload: dict, subgraph: Subgraph, difficulty: str) -> MCQ:
    options = payload.get("options") or {}
    options = {str(k).upper(): str(v) for k, v in options.items()}
    answer = str(
        payload.get("correct_answer") or payload.get("answer") or ""
    ).strip().upper()
    if answer not in options:
        answer = next(iter(options.keys()), "A")
    return MCQ(
        concept=subgraph.concept,
        difficulty=difficulty,
        question=str(payload.get("question", "")).strip(),
        options=options,
        correct_answer=answer,
        explanation=str(payload.get("explanation", "")).strip(),
    )


def _mock_question(subgraph: Subgraph, difficulty: str) -> MCQ:
    """Deterministic mock used when no API key is configured.

    Stable for a given concept name so the output is reproducible.
    """
    rng = random.Random(subgraph.concept)
    facts = [f for f in subgraph.textual_facts if f] or ["(no facts available)"]
    correct = facts[0]
    distractors = (
        facts[1:4]
        if len(facts) > 1
        else ["Option B", "Option C", "Option D"]
    )
    while len(distractors) < 3:
        distractors.append(f"Distractor {len(distractors) + 1}")
    options_list = [correct] + distractors[:3]
    rng.shuffle(options_list)
    labels = ["A", "B", "C", "D"]
    options = dict(zip(labels, options_list))
    answer_label = labels[options_list.index(correct)]
    return MCQ(
        concept=subgraph.concept,
        difficulty=difficulty,
        question=f"[{difficulty}] Which of the following is associated with '{subgraph.concept}'?",
        options=options,
        correct_answer=answer_label,
        explanation=(
            f"The correct answer is supported by the knowledge graph for "
            f"'{subgraph.concept}'."
        ),
    )
