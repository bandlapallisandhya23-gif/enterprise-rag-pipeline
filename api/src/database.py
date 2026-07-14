import os
import json
import logging
from typing import List, Dict, Any
from sqlalchemy import create_engine, text

logger = logging.getLogger(__name__)

DATABASE_URL = os.environ.get("RAG_DATABASE_URL", "postgresql+psycopg2://postgres:postgres@db:5432/rag_database")

class DatabaseHelper:
    def __init__(self):
        self.engine = create_engine(DATABASE_URL, pool_pre_ping=True)

    def test_connection(self) -> bool:
        try:
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except Exception as e:
            logger.error(f"API database connection error: {e}")
            return False

    def list_documents(self) -> List[Dict[str, Any]]:
        """Lists all ingested documents and their status from the log table."""
        query = """
        SELECT document_name, status, chunk_count, file_size, error_message, created_at, updated_at
        FROM document_ingestion_log
        ORDER BY updated_at DESC;
        """
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(query))
                return [
                    {
                        "document_name": row[0],
                        "status": row[1],
                        "chunk_count": row[2],
                        "file_size": row[3],
                        "error_message": row[4],
                        "created_at": row[5].isoformat() if row[5] else None,
                        "updated_at": row[6].isoformat() if row[6] else None,
                    }
                    for row in result
                ]
        except Exception as e:
            logger.error(f"Error listing documents: {e}")
            return []

    def log_document_status(self, document_name: str, status: str, file_size: int = 0):
        """Creates or updates document status in log."""
        query = """
        INSERT INTO document_ingestion_log (document_name, status, file_size, updated_at)
        VALUES (:doc_name, :status, :file_size, CURRENT_TIMESTAMP)
        ON CONFLICT (document_name) DO UPDATE SET
            status = EXCLUDED.status,
            file_size = CASE WHEN EXCLUDED.file_size > 0 THEN EXCLUDED.file_size ELSE document_ingestion_log.file_size END,
            updated_at = CURRENT_TIMESTAMP;
        """
        try:
            with self.engine.begin() as conn:
                conn.execute(text(query), {
                    "doc_name": document_name,
                    "status": status,
                    "file_size": file_size
                })
        except Exception as e:
            logger.error(f"Failed to log document status from API: {e}")

    def query_similar_chunks(self, embedding: List[float], limit: int = 4) -> List[Dict[str, Any]]:
        """
        Executes similarity search on document_chunks using pgvector's
        cosine distance operator <=> and returning distance metadata.
        """
        # Convert embedding float list to a vector string representation '[0.1, 0.2, ...]'
        vector_str = f"[{','.join(map(str, embedding))}]"
        
        query = """
        SELECT document_name, chunk_index, text_content, metadata, (embedding <=> :vector_str) AS distance
        FROM document_chunks
        ORDER BY distance ASC
        LIMIT :limit;
        """
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(query), {
                    "vector_str": vector_str,
                    "limit": limit
                })
                
                chunks = []
                for row in result:
                    chunks.append({
                        "document_name": row[0],
                        "chunk_index": row[1],
                        "text_content": row[2],
                        "metadata": row[3] if isinstance(row[3], dict) else json.loads(row[3] or '{}'),
                        "similarity_score": round(1 - float(row[4]), 4) if row[4] is not None else 0.0 # Cosine distance to similarity
                    })
                return chunks
        except Exception as e:
            logger.error(f"Error querying similar chunks: {e}")
            raise e
