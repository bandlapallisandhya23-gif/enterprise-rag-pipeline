import json
import logging
from typing import List, Dict, Any
from sqlalchemy import create_engine, text

logger = logging.getLogger(__name__)

class RAGDatabaseClient:
    def __init__(self, db_url: str):
        self.db_url = db_url
        self.engine = create_engine(db_url, pool_pre_ping=True)

    def test_connection(self) -> bool:
        """Tests if the database connection is active."""
        try:
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            return False

    def log_ingestion_status(self, document_name: str, status: str, file_size: int = 0, chunk_count: int = 0, error_message: str = None):
        """Logs document ingestion status in the metadata table."""
        query = """
        INSERT INTO document_ingestion_log (document_name, status, file_size, chunk_count, error_message, updated_at)
        VALUES (:doc_name, :status, :file_size, :chunk_count, :error, CURRENT_TIMESTAMP)
        ON CONFLICT (document_name) DO UPDATE SET
            status = EXCLUDED.status,
            chunk_count = EXCLUDED.chunk_count,
            file_size = CASE WHEN EXCLUDED.file_size > 0 THEN EXCLUDED.file_size ELSE document_ingestion_log.file_size END,
            error_message = EXCLUDED.error_message,
            updated_at = CURRENT_TIMESTAMP;
        """
        try:
            with self.engine.begin() as conn:
                conn.execute(text(query), {
                    "doc_name": document_name,
                    "status": status,
                    "file_size": file_size,
                    "chunk_count": chunk_count,
                    "error": error_message
                })
        except Exception as e:
            logger.error(f"Failed to log ingestion status for {document_name}: {e}")

    def insert_chunks(self, document_name: str, chunks: List[Dict[str, Any]], embeddings: List[List[float]]):
        """
        Inserts document text chunks and their embeddings into the database.
        Clears out any existing chunks for the document first (idempotent ingestion).
        """
        delete_query = "DELETE FROM document_chunks WHERE document_name = :doc_name"
        
        insert_query = """
        INSERT INTO document_chunks (document_name, chunk_index, text_content, embedding, metadata)
        VALUES (:doc_name, :chunk_idx, :content, :embedding, :metadata)
        """

        try:
            with self.engine.begin() as conn:
                # 1. Clear existing chunks to prevent duplicates on reprocessing
                conn.execute(text(delete_query), {"doc_name": document_name})
                
                # 2. Insert new chunks
                for idx, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                    # Format vector as string format: '[0.123, 0.456, ...]'
                    vector_str = f"[{','.join(map(str, embedding))}]"
                    
                    conn.execute(text(insert_query), {
                        "doc_name": document_name,
                        "chunk_idx": idx,
                        "content": chunk["text_content"],
                        "embedding": vector_str,
                        "metadata": json.dumps(chunk["metadata"])
                    })
            logger.info(f"Successfully loaded {len(chunks)} chunks for '{document_name}' into DB.")
        except Exception as e:
            logger.error(f"Failed to insert chunks for {document_name}: {e}")
            raise e
