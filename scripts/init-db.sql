-- Enable the pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Table to store document chunks and their embeddings
CREATE TABLE IF NOT EXISTS document_chunks (
    id SERIAL PRIMARY KEY,
    document_name VARCHAR(255) NOT NULL,
    chunk_index INT NOT NULL,
    text_content TEXT NOT NULL,
    embedding vector(384), -- size 384 for sentence-transformers/all-MiniLM-L6-v2
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index for vector search (using Cosine distance)
CREATE INDEX IF NOT EXISTS document_chunks_cosine_idx 
ON document_chunks 
USING hnsw (embedding vector_cosine_ops);

-- Optional table to keep track of document status/metadata
CREATE TABLE IF NOT EXISTS document_ingestion_log (
    id SERIAL PRIMARY KEY,
    document_name VARCHAR(255) UNIQUE NOT NULL,
    status VARCHAR(50) NOT NULL, -- 'PENDING', 'PROCESSING', 'COMPLETED', 'FAILED'
    chunk_count INT DEFAULT 0,
    file_size INT NOT NULL,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
