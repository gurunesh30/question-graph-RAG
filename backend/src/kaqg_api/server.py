"""FastAPI backend for the KAQG pipeline.

Wraps the existing Python pipelines behind a small set of REST endpoints
so the Next.js frontend can drive ingestion, scoring, retrieval, and
generation without reaching into the internals of each pipeline.
"""
from __future__ import annotations

import logging
import os
import tempfile
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from kaqg.config import get_settings
from kaqg.errors import KAQGError
from kaqg.logging import configure_logging
from kaqg.pipelines.generation import GenerationPipeline, GenerationRequest
from kaqg.pipelines.ingestion import IngestionPipeline
from kaqg.pipelines.retrieval import RetrievalPipeline, RetrievalRequest
from kaqg.pipelines.scoring import ScoringPipeline

from kaqg_api.schemas import (
    GenerateMCQRequest,
    GenerateMCQResponse,
    GraphDataResponse,
    IngestRequest,
    ScoreResponse,
)

configure_logging(os.environ.get("KAQG_LOG_LEVEL", "INFO"))
LOGGER = logging.getLogger("kaqg.api.server")

app = FastAPI(
    title="KAQG API",
    version="0.2.0",
    description="Knowledge Augmented Question Generation REST API.",
)

# CORS for the Next.js frontend (default Next port 3000).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _settings() -> Any:
    return get_settings()


def _graph_data_from_neo4j() -> GraphDataResponse:
    """Pull nodes + edges from Neo4j in a format React Flow can consume."""
    from kaqg.clients.neo4j import Neo4jClient
    from kaqg.domain.cypher import NODE_COUNTS_QUERY

    client = Neo4jClient()
    client.connect()
    try:
        with client.session() as session:
            rows = session.execute_read(
                """
                MATCH (n)-[r]->(m)
                RETURN elementId(n) AS n_id,
                       elementId(m) AS m_id,
                       labels(n)[0] AS n_label,
                       m.name AS m_name,
                       n.name AS n_name,
                       m.labels(m)[0] AS m_label,
                       type(r) AS r_type
                """
            )
    finally:
        client.close()

    nodes: dict[str, dict] = {}
    edges: list[dict] = []
    for row in rows:
        nid = row["n_id"]
        if nid not in nodes:
            nodes[nid] = {
                "id": nid,
                "label": row["n_label"],
                "type": row["n_label"],
                "name": row["n_name"] or nid,
                "properties": {},
            }
        edges.append({
            "id": f"{row['n_id']}::{row['m_id']}::{row['r_type']}",
            "source": row["n_id"],
            "target": row["m_id"],
            "type": row["r_type"],
        })
    return GraphDataResponse(
        nodes=[GraphNode(**v) for v in nodes.values()],
        edges=[GraphEdge(**e) for e in edges],
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "version": app.version}


@app.post("/api/ingest-pdf")
async def ingest_pdf(
    file: UploadFile = File(..., description="Syllabus PDF"),
    model: str | None = Form(None),
) -> JSONResponse:
    """Upload a syllabus PDF and run the full ingest pipeline."""
    settings = _settings()
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="File must be a .pdf")
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(await file.read())
            tmp_path = Path(tmp.name)
        with IngestionPipeline(settings) as pipe:
            result = pipe.run(tmp_path)
        return JSONResponse({
            "ok": True,
            "pdf": file.filename,
            "char_count": result.char_count,
            "triple_count": result.triple_count,
            "stdout": result.stdout,
        })
    except KAQGError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        try:
            tmp_path.unlink(missing_ok=True)
        except NameError:
            pass


@app.get("/api/graph-data")
async def graph_data() -> GraphDataResponse:
    try:
        return _graph_data_from_neo4j()
    except KAQGError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/score")
async def score() -> ScoreResponse:
    try:
        with ScoringPipeline() as pipe:
            result = pipe.run()
        return ScoreResponse(updated=result.updated, concepts=[c.to_upsert_row() for c in result.concepts])
    except KAQGError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/generate-mcq")
async def generate_mcq(req: GenerateMCQRequest) -> GenerateMCQResponse:
    try:
        with RetrievalPipeline() as retrieval:
            subgraphs = retrieval.run(RetrievalRequest(difficulty=req.difficulty, count=req.count))
        with GenerationPipeline() as generation:
            questions = generation.generate_many(
                subgraphs,
                GenerationRequest(difficulty=req.difficulty, count=req.count, use_mock=req.mock),
            )
        return GenerateMCQResponse(
            difficulty=req.difficulty,
            count=len(questions),
            mode="mock" if req.mock else "live",
            questions=questions,
        )
    except KAQGError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/")
async def root() -> dict:
    return {"name": "KAQG API", "version": app.version, "docs": "/docs"}