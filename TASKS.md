# KAQG Project Task Board

## Status Legend
- [x] Completed
- [/] In Progress
- [ ] Pending

---

## Phase 1: Ingestion & Triplet Extraction
- [x] Set up project directory structure and Rust workspace
- [x] Configure `.env` environment variables (`OPENROUTER_API_KEY`, `NEO4J_URI`, `NEO4J_PASSWORD`)
- [x] Create Python orchestrator (`main.py`) for OpenRouter API interaction
- [x] Build JSON schema constraints for triples (`head`, `head_type`, `relation`, `tail`, `tail_type`)

## Phase 2: Rust High-Performance Graph Ingestion
- [x] Configure `Cargo.toml` with `neo4rs`, `tokio`, and `serde`
- [x] Resolve `neo4rs` Bolt protocol connection and TLS settings (`bolt+ssc://`)
- [x] Implement atomic Cypher transaction streaming in Rust (`rust_kg_engine/src/main.rs`)
- [x] Verify graph visual integrity in Neo4j Browser (`MATCH (n)-[r]->(m) RETURN n,r,m`)

## Phase 3: PDF Processing & Schema Hardening
- [x] Integrate `pdf-extract` crate into Rust core
- [x] Implement CLI flag (`--extract-pdf`) to stream PDF text to stdout
- [x] Harden LLM prompt to eliminate floating/isolated nodes (`INCLUDE_IN` enforcement)
- [x] Test end-to-end processing on multi-page course syllabus (`syllabus.pdf`)

---

## Phase 4: Concept Centrality & Difficulty Scoring Engine
- [x] **Task 4.1:** Write Cypher query module to compute Degree Centrality for all `concept` nodes
- [x] **Task 4.2:** Implement Rust PageRank calculation service using `neo4rs`
- [x] **Task 4.3:** Normalize raw centrality scores into normalized difficulty scores ($b \in [0.1, 1.0]$)
- [x] **Task 4.4:** Batch update Neo4j `concept` nodes with `difficulty` and `centrality` properties
- [x] **Task 4.5:** Create CLI command `python main.py --score` to trigger scoring execution

---

## Phase 5: Question Generation & Retrieval System
- [x] **Task 5.1:** Build Subgraph Retrieval Sampler (Extract target concept + connected `textual` facts + parent `hierarchy`)
- [x] **Task 5.2:** Implement Difficulty Filter (Filter subgraphs by requested difficulty: Easy $b < 0.4$, Medium $0.4 \le b < 0.7$, Hard $b \ge 0.7$)
- [x] **Task 5.3:** Create KAQG Question Generation Prompt template in Python
- [x] **Task 5.4:** Generate structured MCQ output JSON (Question, Options A/B/C/D, Correct Answer, Explanation)
- [x] **Task 5.5:** Implement CLI export flag (`python main.py --generate-qg --difficulty hard --output questions.json`)
- [x] **Task 5.6:** Final end-to-end verification and performance benchmarks
