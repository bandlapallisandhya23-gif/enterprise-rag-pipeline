import os
import shutil
import logging
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from sentence_transformers import SentenceTransformer

# Import plugins/utilities
from utils.pdf_processor import PDFProcessor
from utils.db_client import RAGDatabaseClient

# Setup logger
logger = logging.getLogger(__name__)

# Defaults and Constants
DEFAULT_ARGS = {
    'owner': 'data-engineering',
    'depends_on_past': False,
    'start_date': datetime(2026, 1, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=2),
}

DATA_DIR = os.environ.get("DATA_DIR", "/app/data")
INPUT_DIR = os.path.join(DATA_DIR, "input")
PROCESSED_DIR = os.path.join(DATA_DIR, "processed")
DATABASE_URL = os.environ.get("RAG_DATABASE_URL", "postgresql+psycopg2://postgres:postgres@db:5432/rag_database")
MODEL_NAME = os.environ.get("EMBEDDING_MODEL_NAME", "sentence-transformers/all-MiniLM-L6-v2")

def setup_directories():
    """Ensure data directories exist."""
    os.makedirs(INPUT_DIR, exist_ok=True)
    os.makedirs(PROCESSED_DIR, exist_ok=True)
    logger.info(f"Verified directories: {INPUT_DIR}, {PROCESSED_DIR}")

def process_incoming_documents():
    """Scans input directory for PDFs, processes text chunks, generates embeddings, and saves to PG."""
    setup_directories()
    
    # 1. Initialize Database Client
    db_client = RAGDatabaseClient(DATABASE_URL)
    if not db_client.test_connection():
        raise ConnectionError("Cannot connect to pgvector PostgreSQL database.")

    # 2. Find all PDFs in input directory
    files = [f for f in os.listdir(INPUT_DIR) if f.lower().endswith('.pdf')]
    if not files:
        logger.info("No PDF files found in input directory.")
        return

    logger.info(f"Found {len(files)} files to process: {files}")

    # 3. Load Embedding Model (cached inside Docker image)
    logger.info(f"Loading embedding model: {MODEL_NAME}")
    model = SentenceTransformer(MODEL_NAME)
    
    # 4. Initialize PDF Processor
    pdf_processor = PDFProcessor(chunk_size=500, chunk_overlap=50)

    for filename in files:
        file_path = os.path.join(INPUT_DIR, filename)
        file_size = os.path.getsize(file_path)
        logger.info(f"Processing document: {filename} ({file_size} bytes)")
        
        # Log status as processing
        db_client.log_ingestion_status(filename, "PROCESSING", file_size=file_size)

        try:
            # Step A: Extract text & chunk
            chunks = pdf_processor.extract_and_chunk(file_path)
            if not chunks:
                raise ValueError("No text extracted from document.")

            # Step B: Generate Embeddings
            texts_to_embed = [chunk["text_content"] for chunk in chunks]
            logger.info(f"Generating embeddings for {len(texts_to_embed)} chunks...")
            embeddings = model.encode(texts_to_embed, show_progress_bar=False).tolist()

            # Step C: Save to Database
            db_client.insert_chunks(filename, chunks, embeddings)

            # Step D: Move to processed/archived folder
            dest_path = os.path.join(PROCESSED_DIR, filename)
            # Handle duplicate names in processed by appending timestamp
            if os.path.exists(dest_path):
                base, ext = os.path.splitext(filename)
                dest_path = os.path.join(PROCESSED_DIR, f"{base}_{int(datetime.now().timestamp())}{ext}")
            
            shutil.move(file_path, dest_path)
            logger.info(f"Moved {filename} to {dest_path}")

            # Log status as completed
            db_client.log_ingestion_status(filename, "COMPLETED", chunk_count=len(chunks))

        except Exception as e:
            logger.error(f"Failed to process document {filename}: {e}")
            db_client.log_ingestion_status(filename, "FAILED", error_message=str(e))
            # Continue processing remaining files

with DAG(
    'enterprise_rag_pdf_ingestion',
    default_args=DEFAULT_ARGS,
    description='Ingest PDFs, extract chunks, generate vector embeddings, and store in pgvector',
    schedule_interval='*/1 * * * *',  # Run every minute
    catchup=False,
    tags=['rag', 'ingestion'],
) as dag:

    process_docs_task = PythonOperator(
        task_id='process_incoming_documents',
        python_callable=process_incoming_documents,
    )
