import os
import logging
from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Dict, Any

from src.database import DatabaseHelper
from src.chain import RAGService

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Enterprise RAG Data Pipeline API",
    description="REST API for uploading documents and performing Q&A against PostgreSQL pgvector vector store",
    version="1.0.0"
)

# Enable CORS for frontend integrations
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
db_helper = DatabaseHelper()

# RAG Service will load the SentenceTransformer model on startup.
# We do a basic check here.
rag_service = None

@app.on_event("startup")
def startup_event():
    global rag_service
    logger.info("Initializing database connection...")
    if not db_helper.test_connection():
        logger.error("Failed to connect to database at startup. Ensure Postgres is running.")
    logger.info("Initializing RAG service and loading embeddings encoder...")
    rag_service = RAGService(db_helper)
    logger.info("API Startup sequence complete.")

# Pydantic Schemas
class QueryRequest(BaseModel):
    question: str = Field(..., description="The query or question to ask the RAG pipeline.")
    limit: int = Field(4, ge=1, le=10, description="The maximum number of document chunks to retrieve.")

class QueryResponse(BaseModel):
    question: str
    answer: str
    sources: List[Dict[str, Any]]
    mode: str

class DocumentInfo(BaseModel):
    document_name: str
    status: str
    chunk_count: int
    file_size: int
    error_message: Any
    created_at: Any
    updated_at: Any

# Routes
@app.get("/health", tags=["System"])
def health_check():
    """Validates api state and connection to PostgreSQL database."""
    db_ok = db_helper.test_connection()
    return {
        "status": "healthy" if db_ok else "degraded",
        "database_connected": db_ok,
        "embedding_model": os.environ.get("EMBEDDING_MODEL_NAME", "sentence-transformers/all-MiniLM-L6-v2")
    }

@app.get("/documents", response_model=List[DocumentInfo], tags=["Documents"])
def get_documents():
    """Lists all documents and their ingestion pipeline statuses."""
    return db_helper.list_documents()

@app.post("/documents/upload", tags=["Documents"])
async def upload_document(file: UploadFile = File(...)):
    """
    Uploads a PDF document to the shared input directory. 
    This automatically triggers the Airflow ingestion DAG.
    """
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF documents are supported.")

    data_dir = os.environ.get("DATA_DIR", "/app/data")
    input_dir = os.path.join(data_dir, "input")
    os.makedirs(input_dir, exist_ok=True)

    dest_path = os.path.join(input_dir, file.filename)

    try:
        # Save file to the shared ingestion volume
        with open(dest_path, "wb") as buffer:
            shutil = None # Import locally to avoid scope shadowing
            import shutil
            shutil.copyfileobj(file.file, buffer)
            
        file_size = os.path.getsize(dest_path)
        logger.info(f"File uploaded via API: {file.filename} ({file_size} bytes)")
        
        # Log ingestion as PENDING in tracking table
        db_helper.log_document_status(file.filename, "PENDING", file_size=file_size)
        
        return {
            "message": f"Successfully uploaded {file.filename}. Ingestion pipeline triggered.",
            "filename": file.filename,
            "file_size_bytes": file_size,
            "status": "PENDING"
        }
    except Exception as e:
        logger.error(f"Failed to upload file {file.filename}: {e}")
        # Clean up if partial write occurred
        if os.path.exists(dest_path):
            os.remove(dest_path)
        raise HTTPException(status_code=500, detail=f"File save error: {str(e)}")

@app.post("/query", response_model=QueryResponse, tags=["Retrieval Q&A"])
def ask_question(request: QueryRequest):
    """
    Performs vector similarity search against pgvector to extract matching chunks, 
    and answers the question using LangChain.
    """
    if not rag_service:
        raise HTTPException(status_code=503, detail="RAG Service is not fully initialized yet.")
    
    try:
        result = rag_service.query(request.question, limit=request.limit)
        return result
    except Exception as e:
        logger.error(f"Error querying RAG system: {e}")
        raise HTTPException(status_code=500, detail=f"Query error: {str(e)}")
