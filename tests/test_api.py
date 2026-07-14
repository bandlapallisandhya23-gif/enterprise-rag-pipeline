import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

# Import the FastAPI application
from main import app

client = TestClient(app)

@pytest.fixture(autouse=True)
def mock_dependencies():
    """Mock the DatabaseHelper and RAGService instances to isolate endpoint testing."""
    with patch("main.db_helper") as mock_db, \
         patch("main.rag_service") as mock_rag:
        
        # Setup DB mock returns
        mock_db.test_connection.return_value = True
        mock_db.list_documents.return_value = [
            {
                "document_name": "corporate_policy.pdf",
                "status": "COMPLETED",
                "chunk_count": 12,
                "file_size": 20485,
                "error_message": None,
                "created_at": "2026-07-13T12:00:00",
                "updated_at": "2026-07-13T12:01:00"
            }
        ]
        
        # Setup RAG service mock returns
        mock_rag.query.return_value = {
            "question": "What is the vacation policy?",
            "answer": "All full-time employees are allocated 20 days of paid time off (PTO) annually.",
            "sources": [
                {
                    "document_name": "corporate_policy.pdf",
                    "page": 1,
                    "similarity_score": 0.895,
                    "snippet": "Vacation Policy: All full-time employees are allocated 20 days..."
                }
            ],
            "mode": "offline-mock"
        }
        
        yield mock_db, mock_rag

def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["database_connected"] is True

def test_get_documents_endpoint():
    response = client.get("/documents")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["document_name"] == "corporate_policy.pdf"
    assert data[0]["status"] == "COMPLETED"

def test_query_endpoint():
    payload = {
        "question": "What is the vacation policy?",
        "limit": 3
    }
    response = client.post("/query", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["question"] == "What is the vacation policy?"
    assert "answer" in data
    assert len(data["sources"]) == 1
    assert data["sources"][0]["document_name"] == "corporate_policy.pdf"

def test_upload_invalid_file_type():
    # Uploading a txt file instead of a PDF should fail with a 400
    files = {"file": ("test.txt", b"some plain text content", "text/plain")}
    response = client.post("/documents/upload", files=files)
    assert response.status_code == 400
    assert "Only PDF documents are supported" in response.json()["detail"]

from unittest.mock import patch, MagicMock, mock_open

@patch("shutil.copyfileobj")
@patch("builtins.open", new_callable=mock_open)
@patch("os.path.getsize", return_value=1234)
def test_upload_pdf_success(mock_size, mock_file, mock_copyfileobj):
    # Uploading a PDF should succeed
    files = {"file": ("test.pdf", b"%PDF-1.4 mock content", "application/pdf")}
    response = client.post("/documents/upload", files=files)
    assert response.status_code == 200
    data = response.json()
    assert "triggered" in data["message"]
    assert data["filename"] == "test.pdf"
    assert data["status"] == "PENDING"

