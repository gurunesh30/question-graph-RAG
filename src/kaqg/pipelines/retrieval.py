"""Subgraph retrieval pipeline (Phase 5, step 1)."""
from __future__ import annotations

import logging
from dataclasses import dataclass

from kaqg.clients.neo4j import Neo4jClient
from kaqg.config import Settings, get_settings
from kaqg.domain.cypher import DIFFICULTY_BAND_QUERY, SUBGRAPH_EXPANSION_QUERY
from kaqg.domain.models import Subgraph
from kaqg.errors import ValidationError

LOGGER = logging.getLogger("kaqg.retrieval")


@dataclass(slots=True)
class RetrievalRequest:
    difficulty: str = "medium"
    count: int = 5


class RetrievalPipeline:
    """Pick concepts inside a difficulty band and expand their neighborhoods."""

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        neo4j: Neo4jClient | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._neo4j = neo4j or Neo4jClient(self._settings)

    def run(self, request: RetrievalRequest) -> list[Subgraph]:
        band = self._resolve_band(request.difficulty)
        if request.count <= 0:
            raise ValidationError("count must be positive")
        self._neo4j.connect()
        with self._neo4j.session() as session:
            seeds = self._sample(session, band, request.count)
            return [self._expand(session, s) for s in seeds]

    # --------------------------------------------------------------- helpers

    def _resolve_band(self, difficulty: str) -> tuple[float, float]:
        key = difficulty.lower()
        if key not in self._settings.difficulty_bands:
            raise ValidationError(
                f"Unknown difficulty '{difficulty}'. "
                f"Expected one of {list(self._settings.difficulty_bands)}"
            )
        return self._settings.difficulty_bands[key]

    @staticmethod
    def _sample(session, band: tuple[float, float], limit: int) -> list[Subgraph]:
        low, high = band
        rows = session.execute_read(
            DIFFICULTY_BAND_QUERY, min_b=low, max_b=high, limit=limit
        )
        return [
            Subgraph(
                concept=row["concept"],
                difficulty=float(row["difficulty"] or 0.0),
                centrality=float(row["centrality"] or 0.0),
            )
            for row in rows
        ]

    @staticmethod
    def _expand(session, subgraph: Subgraph) -> Subgraph:
        rows = session.execute_read(
            SUBGRAPH_EXPANSION_QUERY, concept_name=subgraph.concept
        )
        if not rows:
            return subgraph
        row = rows[0]
        subgraph.textual_facts = [t for t in (row.get("textual_facts") or []) if t]
        subgraph.hierarchy_parents = [h for h in (row.get("hierarchy_parents") or []) if h]
        return subgraph

    def close(self) -> None:
        self._neo4j.close()

    def __enter__(self) -> "RetrievalPipeline":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
