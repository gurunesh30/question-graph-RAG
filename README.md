
# KAQG Knowledge Graph Generator

A high-performance hybrid system (**60% Python / 40% Rust**) built to parse educational syllabi, extract structured domain entities using LLMs via OpenRouter, and ingest multi-layered Knowledge Graphs into **Neo4j AuraDB**.

Built following the **Knowledge Augmented Question Generation (KAQG)** paper specification for structured domain retrieval and concept centrality modeling.

---

## 🏗️ System Architecture


```

```
                            +-------------------+
                            |    syllabus.txt   |
                            +---------+---------+
                                      |
                                      v

```

+----------------------------------------------------------------------------------+
|                                  PYTHON (60%)                                    |
|  • Reads input syllabus text                                                     |
|  • Queries OpenRouter API (GPT-4o-mini) with structured JSON schema constraints  |
|  • Validates triples (hierarchy, concept, textual)                              |
|  • Pipes payload into Rust Native Binary via Stdin                               |
+-----------------------------------------+----------------------------------------+
|
| (Stdio Pipe)
v
+----------------------------------------------------------------------------------+
|                                   RUST (40%)                                     |
|  • Deserializes JSON payload concurrently                                       |
|  • Establishes native Bolt protocol session with Neo4j AuraDB                    |
|  • Executes Cypher MERGE queries within an explicit atomic transaction           |
|  • Handles low-level network and database stream optimization                    |
+-----------------------------------------+----------------------------------------+
|
v
+-------------------+
|   Neo4j AuraDB    |
+-------------------+

```

---

## 📁 Repository Structure

```text
.
├── .env                      # Environment variables (API keys & Cloud URIs)
├── .gitignore                # Prevents committing secrets & build target artifacts
├── README.md                 # Project documentation
├── requirements.txt          # Python dependencies
├── main.py                   # Python LLM orchestrator & subprocess manager
├── syllabus.txt              # Input syllabus dataset
└── rust_kg_engine/           # Rust High-Performance Engine
    ├── Cargo.toml            # Rust dependencies (neo4rs, tokio, serde)
    └── src/
        └── main.rs           # Native Neo4j transaction & graph ingestion core

```

---

## 📐 Graph Schema (KAQG Paper Spec)

The extracted graph strictly adheres to the three-tiered node hierarchy defined in the KAQG architecture:

| Node Label | Type Code | Description | Example |
| --- | --- | --- | --- |
| **`hierarchy`** | $N_{hierarchy}$ | Syllabus units, chapters, or structural modules | `Unit 1: Process Management` |
| **`concept`** | $N_{concept}$ | Core theoretical academic subjects | `CPU Scheduling` |
| **`textual`** | $N_{text}$ | Granular definitions, algorithms, or factual specifics | `Round Robin Algorithm` |

### Allowed Relationships

* `PART_OF`: Connects structural elements (`hierarchy` $\rightarrow$ `hierarchy`).
* `INCLUDE_IN`: Connects core concepts to units (`concept` $\rightarrow$ `hierarchy`).
* `IS_A`: Connects granular facts/definitions to concepts (`textual` $\rightarrow$ `concept`).

---

## 🚀 Getting Started

### Prerequisites

* **System:** Linux (Fedora/Ubuntu/Debian), macOS, or WSL2.
* **Languages:** Python 3.10+ and Rust / Cargo (1.75+).
* **Database:** Free Cloud Instance on [Neo4j AuraDB](https://www.google.com/search?q=https://neo4j.com/cloud/aura/).

---

### 1. Installation

Clone the repository and install the Python dependencies:

```bash
# Clone the repository
git clone [https://github.com/your-username/kaqg-kg-builder.git](https://github.com/your-username/kaqg-kg-builder.git)
cd kaqg-kg-builder

# Install Python packages
pip install -r requirements.txt

```

---

### 2. Build the Rust Engine Core

Before running the main script, compile the Rust binary into a release release binary:

```bash
cd rust_kg_engine
cargo build --release
cd ..

```

---

### 3. Environment Configuration

Create a `.env` file in the root directory:

```bash
cat << 'EOF' > .env
OPENROUTER_API_KEY=your_openrouter_api_key_here
NEO4J_URI=bolt+ssc://<YOUR-INSTANCE-ID>.databases.neo4j.io:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_auradb_password_here
EOF

```

> 💡 **Note on Connection URIs:** Use the `bolt+ssc://` or `neo4j+ssc://` scheme when connecting to Neo4j AuraDB from Linux to ensure smooth TLS verification handshakes.

---

### 4. Running the Pipeline

Ensure your target text is in `syllabus.txt`, then run:

```bash
python3 main.py

```

---

## 📊 Visualizing Results in Neo4j Browser

1. Log in to your **Neo4j Aura Console**.
2. Open the **Query / Neo4j Browser** tool for your instance.

### Query 1: Display Full Graph Structure

```cypher
MATCH (n) RETURN n LIMIT 100

```

### Query 2: Compute Structural Concept Centrality

Derive central concept node weightings based on associate textual facts:

```cypher
MATCH (c:concept)<-[:IS_A]-(t:textual)
RETURN c.name AS Concept, count(t) AS DetailCount
ORDER BY DetailCount DESC

```

---

## 🛠️ Tech Stack

* **Python:** `requests`, `python-dotenv`, `subprocess`, `neo4j` driver
* **Rust:** `tokio` (Async runtime), `serde` & `serde_json` (Deserialization), `neo4rs` (Async Bolt driver), `pdf-extract`
* **Rust binaries:** `rust_kg_engine` (PDF extraction + Neo4j ingestion), `pagerank` (PageRank power-iteration micro-service)
* **LLM Engine:** GPT-4o-mini via OpenRouter API
* **Graph Engine:** Neo4j 5+ (AuraDB Cloud)

---

## 🎯 CLI Usage

```bash
# Phase 1-3: PDF → triples → Neo4j
python main.py syllabus.pdf

# Phase 4: Centrality + IRT difficulty scoring
python main.py --score

# Phase 5: Generate MCQ question bank (writes <difficulty>.json)
python main.py --generate-qg --difficulty hard --count 5 --output hard.json
```

Difficulty bands map to the IRT range `[0.1, 1.0]` as follows:

| Difficulty | Range          |
|------------|----------------|
| easy       | `b < 0.4`      |
| medium     | `0.4 ≤ b < 0.7`|
| hard       | `b ≥ 0.7`      |

Run the offline smoke tests with:

```bash
python tests/test_smoke.py
```

The full end-to-end pipeline (PDF → ingest → score → sample → generate →
export) can be exercised with a single command. It runs live when Neo4j
is reachable and transparently falls back to an offline dry-run otherwise:

```bash
make e2e DIFF=hard N=5 OUT=hard.json
# or directly:
python tests/e2e_pipeline.py --difficulty hard --count 5 --output hard.json
```

Verify the Neo4j driver connection with:

```bash
python tests/verify_neo4j.py
```

---

## 📄 License

MIT License. Free to use and modify for academic and research purposes.
