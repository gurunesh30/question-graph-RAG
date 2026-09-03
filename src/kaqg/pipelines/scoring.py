"""Scoring pipeline: compute degree → IRT difficulty + PageRank centrality → write back."""
from __future__ import annotations

import logging
from dataclasses import dataclass

from kaqg.clients.neo4j import Neo4jClient
from kaqg.clients.pagerank import PageRankClient
from kaqg.config import Settings, get_settings
from kaqg.domain.cypher import (
    CONCEPT_ELEMENT_IDS_QUERY,
    DEGREE_BOUNDS_QUERY,
    DEGREE_CENTRALITY_QUERY,
    PAGERANK_PROJECT_QUERY,
    UPSERT_DIFFICULTY_QUERY,
)
from kaqg.domain.irt import IRTDifficulty, fuse_centrality
from kaqg.domain.models import ConceptScore

LOGGER = logging.getLogger("kaqg.scoring")


@dataclass(slots=True)
class ScoringResult:
    updated: int
    concepts: list[ConceptScore]


class ScoringPipeline:
    """Phase 4 orchestrator: IRT difficulty + PageRank centrality scoring."""

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        neo4j: Neo4jClient | None = None,
        pagerank: PageRankClient | None = None,
        irt: IRTDifficulty | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._neo4j = neo4j or Neo4jClient(self._settings)
        self._pagerank = pagerank or PageRankClient(self._settings)
        self._irt = irt or IRTDifficulty(
            min_difficulty=self._settings.min_difficulty,
            max_difficulty=self._settings.max_difficulty,
        )

    def run(self) -> ScoringResult:
        """Compute scores and persist them to Neo4j."""
        self._neo4j.connect()
        with self._neo4j.session() as session:
            degrees = self._fetch_degrees(session)
            if not degrees:
                LOGGER.warning("No concept nodes found in the graph")
                return ScoringResult(updated=0, concepts=[])
            bounds = self._fetch_bounds(session)
            element_id_map, edges = self._fetch_pagerank_input(session)
            pagerank_scores = self._pagerank.rank(edges)
            min_deg, max_deg = bounds

            scores = [
                ConceptScore(
                    name=concept,
                    degree=deg,
                    centrality=fuse_centrality(
                        deg,
                        pagerank_scores.get(element_id_map.get(concept, -1), 0.0),
                    ),
                    difficulty=self._irt.compute(deg, min_deg, max_deg),
                )
                for concept, deg in degrees.items()
            ]
            updated = self._persist(session, scores)
        LOGGER.info("Updated %d concept nodes with degree/centrality/difficulty", updated)
        return ScoringResult(updated=updated, concepts=scores)

    # --------------------------------------------------------------- helpers

    @staticmethod
    def _fetch_degrees(session) -> dict[str, int]:
        rows = session.execute_read(DEGREE_CENTRALITY_QUERY)
        return {row["concept"]: int(row["degree"] or 0) for row in rows}

    @staticmethod
    def _fetch_bounds(session) -> tuple[int, int]:
        rows = session.execute_read(DEGREE_BOUNDS_QUERY)
        if not rows:
            return 0, 0
        row = rows[0]
        return int(row["min_deg"] or 0), int(row["max_deg"] or 0)

    @staticmethod
    def _fetch_pagerank_input(session) -> tuple[dict[str, int], list[dict]]:
        """Return ``(concept_name -> int_id, edge_list)``.

        We assign sequential integer ids because the Rust PageRank binary
        uses ``u64`` keys and Neo4j 5.x ``elementId()`` returns strings.
        """
        node_rows = session.execute_read(CONCEPT_ELEMENT_IDS_QUERY)
        eid_to_int = {row["eid"]: idx for idx, row in enumerate(node_rows)}
        edge_rows = session.execute_read(PAGERANK_PROJECT_QUERY)
        edges = [
            {"src": eid_to_int[r["src"]], "dst": eid_to_int[r["dst"]]}
            for r in edge_rows
            if r["src"] in eid_to_int and r["dst"] in eid_to_int
        ]
        concept_id_map: dict[str, int] = {
            row["name"]: eid_to_int[row["eid"]]
            for row in node_rows
            if row.get("label") == "concept" and row.get("name")
        }
        return concept_id_map, edges

    @staticmethod
    def _persist(session, scores: list[ConceptScore]) -> int:
        if not scores:
            return 0
        rows = [s.to_upsert_row() for s in scores]
        result = session.execute_write(UPSERT_DIFFICULTY_QUERY, rows=rows)
        if not result:
            return 0
        return int(result[0].get("updated", 0))

    def close(self) -> None:
        self._neo4j.close()

    def __enter__(self) -> "ScoringPipeline":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
