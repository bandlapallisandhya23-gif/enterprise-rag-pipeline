import time
import requests
import os
import sys

API_URL = "http://localhost:8000"

def print_banner(text):
    print("=" * 60)
    print(f" {text} ".center(60, "="))
    print("=" * 60)

def test_health():
    print_banner("Checking Health Endpoint")
    try:
        r = requests.get(f"{API_URL}/health")
        print(f"Status Code: {r.status_code}")
        print(r.json())
        return r.status_code == 200
    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to API. Is FastAPI running on port 8000?")
        return False

def test_list_documents():
    print_banner("Listing Ingested Documents")
    r = requests.get(f"{API_URL}/documents")
    print(f"Status Code: {r.status_code}")
    docs = r.json()
    for doc in docs:
        print(f"- {doc['document_name']} | Status: {doc['status']} | Chunks: {doc['chunk_count']}")
    return docs

def test_upload(file_path):
    print_banner(f"Uploading PDF: {os.path.basename(file_path)}")
    if not os.path.exists(file_path):
        print(f"Error: File not found at {file_path}")
        return False
        
    with open(file_path, 'rb') as f:
        files = {'file': (os.path.basename(file_path), f, 'application/pdf')}
        r = requests.post(f"{API_URL}/documents/upload", files=files)
        print(f"Status Code: {r.status_code}")
        print(r.json())
        return r.status_code == 200

def test_query(question):
    print_banner(f"Querying RAG: '{question}'")
    payload = {
        "question": question,
        "limit": 3
    }
    r = requests.post(f"{API_URL}/query", json=payload)
    print(f"Status Code: {r.status_code}")
    response = r.json()
    print("\n[ANSWER]")
    print(response.get("answer"))
    print("\n[SOURCES]")
    for src in response.get("sources", []):
        print(f"- {src['document_name']} (Page {src['page']}) | Similarity: {src['similarity_score']}")
        print(f"  Snippet: {src['snippet']}")

if __name__ == "__main__":
    if not test_health():
        sys.exit(1)
        
    # Find any sample files in the project
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sample_policy = os.path.join(project_root, "data", "input", "corporate_policy.pdf")
    
    # 1. Show existing files
    test_list_documents()
    
    # 2. Try to upload if file exists
    if os.path.exists(sample_policy):
        test_upload(sample_policy)
        print("\nWaiting 5 seconds for Airflow to process (if compose is active)...")
        time.sleep(5)
        test_list_documents()
    else:
        print(f"\nSample PDF not found at {sample_policy}. Run 'python scripts/generate_samples.py' first.")

    # 3. Ask standard policy question
    test_query("What is the policy on vacation rollover?")
    test_query("How many days do we need to work in the office?")
