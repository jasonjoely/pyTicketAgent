-- =============================================================================
-- Ticket dual-space embeddings (pgvector)
-- PostgreSQL + pgvector required
--
-- POC spaces (both 768-d):
--   fastembed → BAAI/bge-base-en-v1.5
--   ollama    → nomic-embed-text
--
-- Example:
--   psql -U postgres -d pyTickets -f database/002_add_ticket_embeddings.sql
-- =============================================================================

\connect "pyTickets"

CREATE EXTENSION IF NOT EXISTS vector;

ALTER TABLE tickets
    ADD COLUMN IF NOT EXISTS embedding_fastembed vector(768),
    ADD COLUMN IF NOT EXISTS embedding_fastembed_model TEXT,
    ADD COLUMN IF NOT EXISTS embedding_fastembed_content_hash TEXT,
    ADD COLUMN IF NOT EXISTS embedding_fastembed_updated_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS embedding_ollama vector(768),
    ADD COLUMN IF NOT EXISTS embedding_ollama_model TEXT,
    ADD COLUMN IF NOT EXISTS embedding_ollama_content_hash TEXT,
    ADD COLUMN IF NOT EXISTS embedding_ollama_updated_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS ix_tickets_embedding_fastembed_hnsw
    ON tickets USING hnsw (embedding_fastembed vector_cosine_ops);

CREATE INDEX IF NOT EXISTS ix_tickets_embedding_ollama_hnsw
    ON tickets USING hnsw (embedding_ollama vector_cosine_ops);
