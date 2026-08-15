import os
import sys
import json
import time
import subprocess
import requests
from dotenv import load_dotenv

# Automatically load key/value pairs from .env into process environment
load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

def load_syllabus(file_path="syllabus.txt"):
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            return f.read()
    return ""

def extract_kg_via_openrouter(syllabus_text):
    print("[Python] Sending extraction prompt to OpenRouter...")
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    
    prompt = f"""
    You are an expert Knowledge Graph builder following the KAQG paper specification.
    Extract a fully connected Knowledge Graph from the syllabus below.
    
    NODE CLASSIFICATION RULES:
    1. 'hierarchy': Units, Chapters, or Subjects (e.g., "Unit 1", "Operating Systems").
    2. 'concept': Core theoretical academic topics (e.g., "Process Management", "CPU Scheduling", "Virtual Memory").
    3. 'textual': Specific algorithms, data structures, or terms (e.g., "PCB", "FCFS", "FIFO", "LRU").

    RELATIONSHIP RULES (CRITICAL):
    1. 'PART_OF': Use ONLY between hierarchy nodes (e.g., "Unit 1" -> PART_OF -> "Operating Systems").
    2. 'INCLUDE_IN': MUST link concepts to their parent hierarchy unit (e.g., "Process Management" -> INCLUDE_IN -> "Unit 1").
    3. 'IS_A': Use ONLY to link specific textual entities/algorithms to their concept (e.g., "Round Robin" -> IS_A -> "CPU Scheduling", "PCB" -> IS_A -> "Process Management").

    Ensure EVERY concept is connected to a unit via INCLUDE_IN so the graph forms a single connected tree/network.

    Return PURE JSON format matching this schema:
    {{
      "triples": [
        {{"head": "Unit 1", "head_type": "hierarchy", "relation": "part_of", "tail": "Operating Systems", "tail_type": "hierarchy"}},
        {{"head": "Process Management", "head_type": "concept", "relation": "include_in", "tail": "Unit 1", "tail_type": "hierarchy"}},
        {{"head": "CPU Scheduling", "head_type": "concept", "relation": "include_in", "tail": "Unit 1", "tail_type": "hierarchy"}},
        {{"head": "PCB", "head_type": "textual", "relation": "is_a", "tail": "Process Management", "tail_type": "concept"}},
        {{"head": "FCFS", "head_type": "textual", "relation": "is_a", "tail": "CPU Scheduling", "tail_type": "concept"}}
      ]
    }}

    Syllabus:
    {syllabus_text}
    """
    
    body = {
        "model": "nvidia/nemotron-3.5-lightning:free",
        "response_format": {"type": "json_object"},
        "messages": [{"role": "user", "content": prompt}]
    }
    
    resp = requests.post(url, headers=headers, json=body)
    resp.raise_for_status()
    
    content = resp.json()["choices"][0]["message"]["content"]
    return json.loads(content)

def invoke_rust_engine(kg_payload):
    print("[Python] Streaming extracted JSON payload to Rust Native Core...")
    rust_binary = "./rust_kg_engine/target/release/rust_kg_engine"
    
    if not os.path.exists(rust_binary):
        print("[Error] Build the Rust binary first using 'cargo build --release' inside rust_kg_engine directory.")
        sys.exit(1)

    # Pass down the existing OS environment (which now includes loaded .env vars)
    process = subprocess.Popen(
        [rust_binary],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=os.environ
    )
    
    stdout, stderr = process.communicate(input=json.dumps(kg_payload))
    
    if process.returncode != 0:
        print(f"[Error in Rust Core]:\n{stderr}")
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
    if not OPENROUTER_API_KEY:
        print("Error: OPENROUTER_API_KEY is missing from .env file.")
        sys.exit(1)
        
    syllabus = load_syllabus()
    extracted_data = extract_kg_via_openrouter(syllabus)
    invoke_rust_engine(extracted_data)
    test()