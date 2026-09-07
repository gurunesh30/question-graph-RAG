# KAQG Backend

FastAPI wrapper that exposes the KAQG pipeline (ingestion, scoring,
retrieval, generation) as a small set of REST endpoints for the Next.js
frontend.

## Endpoints

| Method | Path                | Description                                    |
|--------|---------------------|------------------------------------------------|
| POST   | `/api/ingest-pdf`   | Upload a syllabus PDF, run the full ingest.    |
| GET    | `/api/graph-data`   | Pull nodes + edges from Neo4j for visualization.|
| POST   | `/api/score`        | Compute IRT difficulty for all concept nodes. |
| POST   | `/api/generate-mcq` | Sample subgraphs and generate MCQs.           |

## Run

```bash
cd backend
pip install -e ".[dev]"
uvicorn api.server:app --reload --host 0.0.0.0 --port 8000
```