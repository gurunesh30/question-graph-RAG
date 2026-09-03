# KAQG — Knowledge Augmented Question Generation

A production-grade hybrid **Python / Rust** pipeline for converting course
syllabi into difficulty-calibrated MCQs. Implements the **KAQG paper**
specification end-to-end:

1. **Ingest** — extract text from a syllabus PDF (Rust `pdf-extract`).
2. **Triples** — ask an LLM (OpenRouter) for hierarchical knowledge triples.
3. **Graph** — atomically ingest triples into Neo4j AuraDB (Rust `neo4rs`).
4. **Score** — compute Degree Centrality + PageRank → IRT difficulty in `[0.1, 1.0]`.
5. **Retrieve** — sample subgraphs by difficulty band (`easy` / `medium` / `hard`).
6. **Generate** — graph-conditioned MCQ generation with structured JSON output.

---

## 📁 Project Layout

```
.
├── pyproject.toml              # Build metadata + tool config (ruff, mypy, pytest)
├── .env.example                # Template for required env vars
├── main.py                     # Thin CLI shim
├── Makefile                    # Common dev workflows
├── rust_kg_engine/             # Rust workspace
│   ├── Cargo.toml              # Workspace root
│   └── crates/
│       ├── core/               # Shared types + tracing init
│       ├── ingest/             # `kaqg_ingest` binary (PDF + Neo4j)
│       └── pagerank/           # `kaqg_pagerank` micro-service
├── src/kaqg/                   # Python package
│   ├── cli.py                  # argparse subcommand app
│   ├── config.py               # Typed Settings + validation
│   ├── errors.py               # Exception hierarchy
│   ├── logging.py              # Structured logging
│   ├── export.py               # JSON / Markdown writers
│   ├── clients/                # External-service adapters
│   │   ├── neo4j.py            # Driver + session wrapper
│   │   ├── openrouter.py       # LLM HTTP client
│   │   ├── pagerank.py         # Rust binary wrapper
│   │   ├── ingest.py           # Rust ingest binary wrapper
│   │   └── retry.py            # Bounded exponential backoff
│   ├── domain/                 # Pure data + Cypher + IRT math
│   │   ├── models.py           # Triple, MCQ, Subgraph, QuestionBank, …
│   │   ├── cypher.py           # All Cypher statements in one place
│   │   └── irt.py              # Spec 4.3 IRT formula
│   └── pipelines/              # Orchestration
│       ├── ingestion.py
│       ├── scoring.py
│       ├── retrieval.py
│       └── generation.py
└── tests/
    ├── conftest.py             # Shared pytest fixtures
    ├── unit/                   # Pure, no I/O
    └── integration/            # Live Neo4j (gated by KAQG_LIVE=1)
```

---

## 🚀 Quickstart

```bash
# 1. Install
python3 -m pip install -e ".[dev]"
cp .env.example .env  # then fill in real credentials

# 2. Build the Rust binaries
make build

# 3. Verify your environment
make test
make verify      # round-trips the Neo4j connection

# 4. Run the pipeline
make ingest PDF=syllabus.pdf
make score
make generate DIFF=hard N=5 OUT=hard.json
make e2e PDF=syllabus.pdf DIFF=hard N=5 OUT=e2e.json
```

The CLI is also available directly:

```bash
python -m kaqg.cli --help
python -m kaqg.cli ingest syllabus.pdf
python -m kaqg.cli score
python -m kaqg.cli generate --difficulty hard --count 5 --output hard.json
python -m kaqg.cli verify
python -m kaqg.cli e2e syllabus.pdf --difficulty medium --count 3
```

---

## 🧱 Architecture

```
                +---------------------+
                |  syllabus.pdf       |
                +---------+-----------+
                          |
                          v  (Rust: pdf-extract)
                +---------------------+
                |   kaqg_ingest       |
                +---------+-----------+
                          |  raw text
                          v
                +---------------------+
                |  OpenRouter LLM     |
                +---------+-----------+
                          |  KgPayload (validated)
                          v
                +---------------------+        +--------------------+
                |   kaqg_ingest       | -----> |  Neo4j AuraDB      |
                +---------------------+        +--------------------+
                                                       |
                                  +--------------------+--------------------+
                                  |                    |                    |
                                  v                    v                    v
                       degree + PageRank      subgraph sampler         generation
                       (kaqg_pagerank)        (difficulty band)       (OpenRouter)
                                  |                    |                    |
                                  v                    v                    v
                          c.difficulty in [0.1, 1.0]  Subgraph            MCQ bank
                                                                       (JSON / Markdown)
```

---

## 🧪 Testing

```bash
make test        # 26 fast unit tests, no network
make test-all    # Adds live Neo4j tests (requires KAQG_LIVE=1 + creds)
make lint        # ruff + mypy
```

Live integration tests are skipped by default.  Set `KAQG_LIVE=1` and
populate `.env` to enable them.

---

## 🛠️ Tech Stack

| Layer       | Technology                                                   |
|-------------|--------------------------------------------------------------|
| Orchestration | Python 3.10+ (`argparse`, `dataclasses`, `pathlib`)         |
| LLM         | OpenRouter (`openai/gpt-4o-mini` default)                    |
| Graph DB    | Neo4j 5+ (AuraDB) via the official `neo4j` Python driver     |
| PDF / Neo4j | Rust workspace — `tokio`, `neo4rs`, `pdf-extract`, `anyhow`   |
| PageRank    | Rust workspace — dependency-free power iteration            |
| Logging     | stdlib `logging` with structured format                      |
| Tests       | `pytest`, in-memory fixtures, no external state             |

---

## 📐 Graph Schema (KAQG Spec)

| Node Label     | Type Code     | Description                          | Example            |
|----------------|---------------|--------------------------------------|--------------------|
| `hierarchy`    | N_hierarchy   | Units, chapters, subjects            | `Unit 1: Processes`|
| `concept`      | N_concept     | Core theoretical topics              | `CPU Scheduling`   |
| `textual`      | N_textual     | Granular facts / algorithms          | `Round Robin`      |

Relationships:

* `PART_OF`  — `hierarchy` → `hierarchy`
* `INCLUDE_IN` — `concept` → `hierarchy`
* `IS_A`     — `textual` → `concept`

---

## 📄 License

MIT — free for academic and research use.
