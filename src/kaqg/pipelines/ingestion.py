"""Ingestion pipeline: PDF → KnowledgeGraph → Neo4j (via Rust binary)."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from kaqg.clients.ingest import IngestClient
from kaqg.clients.openrouter import OpenRouterClient
from kaqg.config import Settings, get_settings
from kaqg.domain.models import KnowledgeGraph
from kaqg.errors import IngestionError

LOGGER = logging.getLogger("kaqg.ingestion")

KG_EXTRACTION_PROMPT = """You are an expert Knowledge Graph builder following the KAQG paper specification.
Extract a fully connected Knowledge Graph from the syllabus below.

NODE CLASSIFICATION RULES:
1. 'hierarchy': Units, Chapters, or Subjects.
2. 'concept': Core theoretical academic topics.
3. 'textual': Specific algorithms, data structures, or terms.

RELATIONSHIP RULES:
1. 'PART_OF': Use ONLY between hierarchy nodes.
2. 'INCLUDE_IN': MUST link concepts to their parent hierarchy unit.
3. 'IS_A': Use ONLY to link specific textual entities/algorithms to their concept.

Return PURE JSON format:
{{
  "triples": [
    {{"head": "Unit 1", "head_type": "hierarchy", "relation": "part_of", "tail": "Operating Systems", "tail_type": "hierarchy"}},
    {{"head": "Process Management", "head_type": "concept", "relation": "include_in", "tail": "Unit 1", "tail_type": "hierarchy"}},
    {{"head": "PCB", "head_type": "textual", "relation": "is_a", "tail": "Process Management", "tail_type": "concept"}}
  ]
}}

Syllabus:
{text}
"""


@dataclass(slots=True)
class IngestionResult:
    pdf_path: Path
    char_count: int
    triple_count: int
    stdout: str


class IngestionPipeline:
    """End-to-end Phase 1-3 orchestrator: PDF → LLM → Neo4j."""

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        llm: OpenRouterClient | None = None,
        ingest: IngestClient | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._llm = llm or OpenRouterClient(self._settings)
        self._ingest = ingest or IngestClient(self._settings)

    def close(self) -> None:
        self._llm.close()

    # ------------------------------------------------------------------ API

    def run(self, pdf_path: str | Path) -> IngestionResult:
        pdf_path = Path(pdf_path)
        LOGGER.info("Extracting text from %s", pdf_path)
        text = self._ingest.extract_pdf(pdf_path)
        if not text.strip():
            raise IngestionError(f"PDF '{pdf_path}' produced empty text")
        LOGGER.info("Extracted %d characters; asking LLM for triples", len(text))

        prompt = KG_EXTRACTION_PROMPT.format(text=text)
        payload = self._llm.complete_json(prompt)
        graph = KnowledgeGraph.from_payload(payload)
        LOGGER.info("LLM produced %d validated triples; writing to Neo4j", len(graph.triples))

        stdout = self._ingest.ingest(graph)
        return IngestionResult(
            pdf_path=pdf_path,
            char_count=len(text),
            triple_count=len(graph.triples),
            stdout=stdout,
        )

    def __enter__(self) -> "IngestionPipeline":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
