# KAQG (Knowledge Augmented Question Generation) System Architecture & Roadmap

## 🎯 Project Overview
This project implements a hybrid **60% Python / 40% Rust** pipeline based on the **Knowledge Augmented Question Generation (KAQG)** paper specification. The system ingests course syllabi via Rust PDF extraction, builds a three-tiered Knowledge Graph in Neo4j AuraDB, calculates structural concept centrality, and generates difficulty-calibrated Multiple Choice Questions (MCQs).

---

## 🏗️ Phase-Wise Development Plan

[Phase 1-3: COMPLETE]             [Phase 4: IN PROGRESS]                 [Phase 5: PENDING]
+----------------------+        +--------------------------+        +--------------------------+
| PDF Extraction (Rust)| -----> | Concept Centrality Engine| -----> | Subgraph Retrieval & LLM |
| OpenRouter LLM Parsing|       | • Degree Centrality      |        | Question Generation      |
| Neo4j Ingestion (Rust)|       | • PageRank Weighting     |        | • Difficulty Calibration |
+----------------------+        +--------------------------+        +--------------------------+


### Phase 1: Ingestion & Triplet Extraction (Completed ✅)
* Extract raw text from course syllabus PDFs using `pdf-extract` in Rust.
* Send formatted prompt to OpenRouter API (GPT-4o-mini) to extract structured JSON triples.
* Enforce three-tiered schema: `hierarchy` ($N_{hierarchy}$), `concept` ($N_{concept}$), and `textual` ($N_{textual}$).

### Phase 2: High-Performance Graph Ingestion (Completed ✅)
* Pipe extracted triples from Python to Rust via Stdin.
* Execute atomic Cypher transactions in Neo4j AuraDB using `neo4rs`.
* Enforce directional relationships: `PART_OF`, `INCLUDE_IN`, and `IS_A`.

### Phase 3: OCR & Isolated Node Prevention (Completed ✅)
* Handle multi-page academic syllabus PDFs cleanly.
* Refine LLM prompt rules to eliminate orphan nodes and form unified tree structures.

### Phase 4: Structural Concept Centrality Engine (Current Focus 🚧)
* Implement Cypher/Rust algorithms to calculate **Degree Centrality** and **PageRank** for every `concept` node.
* Map centrality scores to **Item Response Theory (IRT)** difficulty parameters ($b_i \in [0.1, 1.0]$).
* Write calculated difficulty coefficients back to Neo4j node properties (`c.difficulty`).

### Phase 5: KG-Augmented Question Generation Engine (Final Step ⏳)
* Sample target subgraphs from Neo4j based on user-requested difficulty levels.
* Construct graph-conditioned prompts containing:
  * Target Concept & associated `IS_A` details (distractor pool context).
  * Parent Hierarchy Context (`INCLUDE_IN`).
* Generate calibrated MCQs with structured distractor options, correct answer keys, and pedagogical explanations.
* Provide a CLI / REST interface to export question banks in JSON/Markdown format.

---

## 🛠️ Technology Stack
* **Orchestration & LLM Calling:** Python 3.10+ (`requests`, `python-dotenv`)
* **Core Engine & PDF Parsing:** Rust 1.75+ (`tokio`, `serde`, `neo4rs`, `pdf-extract`)
* **Database:** Neo4j AuraDB Cloud
* **LLM Model:** GPT-4o-mini via OpenRouter
