import os
import sys
import json
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
    Extract a Knowledge Graph from this syllabus according to KAQG rules.
    Classify node labels strictly into:
    - 'hierarchy' (Units/Chapters)
    - 'concept' (Core academic subjects)
    - 'textual' (Specific details/facts/algorithms)
    
    Use relations: 'part_of', 'include_in', 'is_a'.
    
    Return pure JSON:
    {{
      "triples": [
        {{"head": "Unit 1", "head_type": "hierarchy", "relation": "part_of", "tail": "Operating Systems", "tail_type": "hierarchy"}},
        {{"head": "PCB", "head_type": "textual", "relation": "is_a", "tail": "Process Management", "tail_type": "concept"}}
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

if __name__ == "__main__":
    if not OPENROUTER_API_KEY:
        print("Error: OPENROUTER_API_KEY is missing from .env file.")
        sys.exit(1)
        
    syllabus = load_syllabus()
    extracted_data = extract_kg_via_openrouter(syllabus)
    invoke_rust_engine(extracted_data)