"""Pipelines package — orchestration of ingestion, scoring, retrieval, generation."""
from kaqg.pipelines.generation import GenerationPipeline
from kaqg.pipelines.ingestion import IngestionPipeline
from kaqg.pipelines.retrieval import RetrievalPipeline
from kaqg.pipelines.scoring import ScoringPipeline

__all__ = [
    "GenerationPipeline",
    "IngestionPipeline",
    "RetrievalPipeline",
    "ScoringPipeline",
]