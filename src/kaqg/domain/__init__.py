"""Domain package for KAQG.

Re-exports the public domain types so callers can do
``from kaqg.domain import MCQ, Subgraph`` etc.
"""
from kaqg.domain.cypher import (
    DEGREE_BOUNDS_QUERY,
    DEGREE_CENTRALITY_QUERY,
    DIFFICULTY_BAND_QUERY,
    PAGERANK_PROJECT_QUERY,
    SUBGRAPH_EXPANSION_QUERY,
    UPSERT_DIFFICULTY_QUERY,
)
from kaqg.domain.irt import (
    IRTDifficulty,
    clamp_difficulty,
    fuse_centrality,
    irt_difficulty,
)
from kaqg.domain.models import (
    DIFFICULTY_BANDS,
    MCQ,
    OPTION_LABELS,
    ConceptScore,
    KnowledgeGraph,
    QuestionBank,
    Subgraph,
    Triple,
    VALID_NODE_TYPES,
    VALID_RELATIONS,
)

__all__ = [
    "ConceptScore",
    "DEGREE_BOUNDS_QUERY",
    "DEGREE_CENTRALITY_QUERY",
    "DIFFICULTY_BAND_QUERY",
    "DIFFICULTY_BANDS",
    "IRT",
    "IRTDifficulty",
    "KnowledgeGraph",
    "MCQ",
    "OPTION_LABELS",
    "PAGERANK_PROJECT_QUERY",
    "QuestionBank",
    "SUBGRAPH_EXPANSION_QUERY",
    "Subgraph",
    "Triple",
    "UPSERT_DIFFICULTY_QUERY",
    "VALID_NODE_TYPES",
    "VALID_RELATIONS",
    "clamp_difficulty",
    "fuse_centrality",
    "irt_difficulty",
]

# Backwards compatibility alias for the IRT numeric helper.
IRT = irt_difficulty