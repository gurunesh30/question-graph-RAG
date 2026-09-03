import os
import sys
import json
import time
import subprocess
import argparse
from pathlib import Path
import requests
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
RUST_BINARY = "./rust_kg_engine/target/release/rust_kg_engine"

def load_syllabus(file_path="syllabus.txt"):
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            return f.read()
    return ""

def extract_text_from_pdf_via_rust(pdf_path):
    """Invokes Rust core to extract text from a PDF document."""
    print(f"[Python] Requesting Rust binary to extract text from '{pdf_path}'...")

    if not os.path.exists(RUST_BINARY):
        print("[Error] Build the Rust binary first using 'cargo build --release' inside rust_kg_engine.")
        sys.exit(1)

    result = subprocess.run(
        [RUST_BINARY, "--extract-pdf", pdf_path],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        print(f"[Error in Rust PDF Extractor]:\n{result.stderr}")
        sys.exit(1)

    extracted_text = result.stdout
    print(f"[Python] Successfully extracted {len(extracted_text)} characters from PDF.")
    return extracted_text

def extract_kg_via_openrouter(text_content):
    print("[Python] Sending extracted syllabus text to OpenRouter...")
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    prompt = f"""
    You are an expert Knowledge Graph builder following the KAQG paper specification.
    Extract a fully connected Knowledge Graph from the syllabus below.

    NODE CLASSIFICATION RULES:
    1. 'hierarchy': Units, Chapters, or Subjects.
    2. 'concept': Core theoretical academic topics.
    3. 'textual': Specific algorithms, data structures, or terms.

    RELATIONSHIP RULES:
    1. 'PART_OF': Use ONLY between hierarchy nodes.
    2. 'INCLUDE_IN': MUST link concepts to their parent hierarchy unit.
    3. 'IS_A': Use ONLY to link specific textual entities/algorithms to their concept.

    Return PURE JSON format:
    {{
      "triples": [
        {{"head": "Unit 1", "head_type": "hierarchy", "relation": "part_of", "tail": "Operating Systems", "tail_type": "hierarchy"}},
        {{"head": "Process Management", "head_type": "concept", "relation": "include_in", "tail": "Unit 1", "tail_type": "hierarchy"}},
        {{"head": "PCB", "head_type": "textual", "relation": "is_a", "tail": "Process Management", "tail_type": "concept"}}
      ]
    }}

    Syllabus:
    {text_content}
    """

    body = {
        "model": "openai/gpt-4o-mini",
        "response_format": {"type": "json_object"},
        "messages": [{"role": "user", "content": prompt}]
    }

    resp = requests.post(url, headers=headers, json=body)
    resp.raise_for_status()
    return json.loads(resp.json()["choices"][0]["message"]["content"])

def invoke_rust_engine_ingest(kg_payload):
    print("[Python] Streaming JSON payload to Rust Core for Neo4j ingestion...")
    process = subprocess.Popen(
        [RUST_BINARY],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=os.environ
    )

    stdout, stderr = process.communicate(input=json.dumps(kg_payload))
    if process.returncode != 0:
        print(f"[Error in Rust Ingestion]:\n{stderr}")
        sys.exit(1)

    print(stdout)

def run_ingestion_pipeline(pdf_file):
    """Phase 1-3: PDF -> triples -> Neo4j."""
    if not os.path.exists(pdf_file):
        print(f"Usage: python main.py <path_to_pdf>")
        print(f"Error: Could not find default file '{pdf_file}'")
        sys.exit(1)

    raw_text = extract_text_from_pdf_via_rust(pdf_file)
    kg_data = extract_kg_via_openrouter(raw_text)
    invoke_rust_engine_ingest(kg_data)

def run_score_pipeline():
    """Phase 4: Centrality + IRT difficulty scoring."""
    from kg.centrality import run_scoring_pipeline
    t0 = time.perf_counter()
    updated = run_scoring_pipeline()
    print(f"[Score] Wrote difficulty scores to {updated} concept nodes in {time.perf_counter() - t0:.3f}s")
    return updated

def run_generate_pipeline(args):
    """Phase 5: Subgraph retrieval -> MCQ generation -> export."""
    from kg.generation import generate_questions
    questions = generate_questions(
        difficulty=args.difficulty,
        count=args.count,
    )
    payload = {
        "difficulty": args.difficulty,
        "count": len(questions),
        "questions": questions,
    }
    output_path = args.output
    if output_path is None:
        base = args.difficulty or "questions"
        output_path = f"{base}.json"
    with open(output_path, "w") as f:
        json.dump(payload, f, indent=2)
    print(f"[Generate] Wrote {len(questions)} questions to '{output_path}'.")
    return output_path

def build_parser():
    parser = argparse.ArgumentParser(
        prog="kaqg",
        description="Knowledge Augmented Question Generation pipeline.",
    )
    parser.add_argument("pdf", nargs="?", default="syllabus.pdf",
                        help="PDF syllabus to ingest (default: syllabus.pdf)")
    parser.add_argument("--score", action="store_true",
                        help="Compute centrality + IRT difficulty for concept nodes.")
    parser.add_argument("--generate-qg", action="store_true",
                        help="Generate MCQ question bank from the Neo4j graph.")
    parser.add_argument("--difficulty", choices=["easy", "medium", "hard"], default="medium",
                        help="Difficulty band for --generate-qg (default: medium).")
    parser.add_argument("--count", type=int, default=5,
                        help="Number of questions to generate (default: 5).")
    parser.add_argument("--output", type=Path, default=None,
                        help="Output file for generated question bank (JSON).")
    return parser

def main():
    args = build_parser().parse_args()

    if args.score:
        run_score_pipeline()
        return

    if args.generate_qg:
        run_generate_pipeline(args)
        return

    run_ingestion_pipeline(args.pdf)

if __name__ == "__main__":
    main()