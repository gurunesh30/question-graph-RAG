import os
import sys
import json
import subprocess
import requests
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
RUST_BINARY = "./rust_kg_engine/target/release/rust_kg_engine"

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

def test():
    if not OPENROUTER_API_KEY:
        print("Error: OPENROUTER_API_KEY is missing from .env file.")
        sys.exit(1)

    print("[Test] Starting KG pipeline benchmark...\n")
    total_start = time.perf_counter()

    # Step 1: Load syllabus
    t0 = time.perf_counter()
    syllabus = load_syllabus()
    t1 = time.perf_counter()
    print(f"[Test] Syllabus loaded            : {t1 - t0:.3f}s")

    # Step 2: LLM extraction via OpenRouter
    t0 = time.perf_counter()
    extracted_data = extract_kg_via_openrouter(syllabus)
    t1 = time.perf_counter()
    print(f"[Test] LLM extraction (OpenRouter): {t1 - t0:.3f}s")

    # Step 3: Rust engine writes to Neo4j
    t0 = time.perf_counter()
    invoke_rust_engine(extracted_data)
    t1 = time.perf_counter()
    print(f"[Test] Rust KG engine (Neo4j)     : {t1 - t0:.3f}s")

    total_end = time.perf_counter()
    print(f"\n[Test] Total KG pipeline time     : {total_end - total_start:.3f}s")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        pdf_file = sys.argv[1]
    else:
        pdf_file = "syllabus.pdf"

    if not os.path.exists(pdf_file):
        print(f"Usage: python main.py <path_to_pdf>")
        print(f"Error: Could not find default file '{pdf_file}'")
        sys.exit(1)

    # Step 1: Extract Text via Rust
    raw_text = extract_text_from_pdf_via_rust(pdf_file)
    
    # Step 2: Extract Triples via LLM
    kg_data = extract_kg_via_openrouter(raw_text)
    
    # Step 3: Ingest Triples into Neo4j via Rust
    invoke_rust_engine_ingest(kg_data)