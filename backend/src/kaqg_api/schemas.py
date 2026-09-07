"""Pydantic models for the KAQG REST API."""
from __future__ import annotations

from pydantic import BaseModel, Field

from kaqg.domain.models import MCQ


class IngestRequest(BaseModel):
    """Request body for the ingest endpoint (optional overrides)."""
    pdf_path: str | None = None
    model: str | None = None  # override OpenRouter model


class GraphNode(BaseModel):
    id: str
    label: str
    type: str
    name: str
    properties: dict[str, object] = Field(default_factory=dict)


class GraphEdge(BaseModel):
    id: str
    source: str
    target: str
    type: str


class GraphDataResponse(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]


class ScoreResponse(BaseModel):
    updated: int
    concepts: list[dict] = Field(default_factory=list)


class GenerateMCQRequest(BaseModel):
    difficulty: str = "medium"
    count: int = 5
    mock: bool = False  # use deterministic mock instead of LLM


class MCQResponse(MCQ):
    pass


class GenerateMCQResponse(BaseModel):
    difficulty: str
    count: int
    mode: str
    questions: list[MCQResponse]