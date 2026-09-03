"""KAQG question generation prompt + LLM call.

Builds a graph-conditioned prompt from a sampled subgraph, sends it to the
OpenRouter API, and parses the structured MCQ JSON response.
"""
from __future__ import annotations

import json
import os
import random
from dataclasses import dataclass
from typing import Optional

import requests
from dotenv import load_dotenv

from kg.retrieval import Subgraph

load_dotenv()

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODEL = os.getenv("KAQG_MODEL", "openai/gpt-4o-mini")
DIFFICULTY_PROMPTS = {
    "easy": "Write a straightforward recall question with one obviously correct option.",
    "medium": "Write an applied question that requires combining two of the listed facts.",
    "hard": "Write a synthesis question requiring inference across the hierarchy and facts.",
}


@dataclass
class MCQ:
    concept: str
    difficulty: str
    question: str
    options: dict[str, str]
    answer: str
    explanation: str

    def as_dict(self) -> dict:
        return {
            "concept": self.concept,
            "difficulty": self.difficulty,
            "question": self.question,
            "options": self.options,
            "answer": self.answer,
            "explanation": self.explanation,
        }


def build_prompt(subgraph: Subgraph, difficulty: str) -> str:
    directive = DIFFICULTY_PROMPTS.get(difficulty.lower(), DIFFICULTY_PROMPTS["medium"])
    return f"""You are an expert exam setter following the KAQG paper specification.
Generate exactly ONE multiple-choice question from the knowledge subgraph below.

Difficulty directive: {directive}

Knowledge Subgraph:
{subgraph.context_block()}

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
  "answer": "A",
  "explanation": "..."
}}
"""


def _headers() -> dict:
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY missing from environment")
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }


def _parse_response(payload: dict, subgraph: Subgraph, difficulty: str) -> MCQ:
    options = payload.get("options") or {}
    options = {str(k).upper(): str(v) for k, v in options.items()}
    answer = str(payload.get("answer", "")).strip().upper()
    if answer not in options:
        # fall back to the first available option label
        answer = next(iter(options.keys()), "A")
    return MCQ(
        concept=subgraph.concept,
        difficulty=difficulty,
        question=str(payload.get("question", "")).strip(),
        options=options,
        answer=answer,
        explanation=str(payload.get("explanation", "")).strip(),
    )


def _mock_question(subgraph: Subgraph, difficulty: str) -> MCQ:
    """Deterministic fallback used when no API key is available.

    Useful for unit tests and offline smoke checks.  Randomness is seeded by
    the concept name so the output is stable for a given graph.
    """
    rng = random.Random(subgraph.concept)
    facts = [f for f in subgraph.textual_facts if f] or ["(no facts available)"]
    correct = facts[0]
    distractors = facts[1:4] if len(facts) > 1 else ["Option B", "Option C", "Option D"]
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
        answer=answer_label,
        explanation=f"The correct answer is supported by the knowledge graph for '{subgraph.concept}'.",
    )


def generate_for_subgraph(subgraph: Subgraph,
                          difficulty: str = "medium",
                          use_llm: bool = True) -> MCQ:
    prompt = build_prompt(subgraph, difficulty)
    if not use_llm or not os.getenv("OPENROUTER_API_KEY"):
        return _mock_question(subgraph, difficulty)

    body = {
        "model": OPENROUTER_MODEL,
        "response_format": {"type": "json_object"},
        "messages": [{"role": "user", "content": prompt}],
    }
    resp = requests.post(OPENROUTER_URL, headers=_headers(), json=body, timeout=60)
    resp.raise_for_status()
    content = resp.json()["choices"][0]["message"]["content"]
    parsed = json.loads(content)
    return _parse_response(parsed, subgraph, difficulty)


def generate_batch(subgraphs: list[Subgraph], difficulty: str = "medium") -> list[MCQ]:
    return [generate_for_subgraph(sg, difficulty) for sg in subgraphs]


if __name__ == "__main__":
    from kg.retrieval import fetch_subgraphs
    for sg in fetch_subgraphs("easy", 2):
        mcq = generate_for_subgraph(sg, "easy", use_llm=False)
        print(mcq.as_dict())