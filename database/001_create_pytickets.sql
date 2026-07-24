-- =============================================================================
-- pyTickets Database Setup
-- PostgreSQL 12+ required (GENERATED ALWAYS AS ... STORED for tsvector)
--
-- Adapted from DFAgent dftickets schema. Database name: pyTickets
--
-- Example:
--   psql -U postgres -f 001_create_pytickets.sql
-- =============================================================================

-- Create database (skip if already exists)
SELECT 'CREATE DATABASE "pyTickets"'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'pyTickets')\gexec

\connect "pyTickets"

-- ---------------------------------------------------------------------------
-- Tickets table
-- id is supplied by import — NOT auto-generated
-- created_at is TIMESTAMPTZ — absolute UTC instant
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS tickets (
    id                  INTEGER         PRIMARY KEY,
    created_at          TIMESTAMPTZ     NOT NULL,
    environment         VARCHAR(20)     NOT NULL,
    service             VARCHAR(30)     NOT NULL,
    title               TEXT            NOT NULL,
    description         TEXT            NOT NULL,
    resolution_summary  TEXT            NOT NULL DEFAULT '',
    tags                TEXT[]          NOT NULL DEFAULT '{}',
    severity            INTEGER         NOT NULL DEFAULT 0 CHECK (severity >= 0),

    -- Full-text search over title, description, and resolution_summary
    search_vector       TSVECTOR GENERATED ALWAYS AS (
        to_tsvector(
            'english',
            coalesce(title, '') || ' ' ||
            coalesce(description, '') || ' ' ||
            coalesce(resolution_summary, '')
        )
    ) STORED
);

-- Filterable column indexes
CREATE INDEX IF NOT EXISTS ix_tickets_environment
    ON tickets (environment);

CREATE INDEX IF NOT EXISTS ix_tickets_service
    ON tickets (service);

CREATE INDEX IF NOT EXISTS ix_tickets_severity
    ON tickets (severity);

CREATE INDEX IF NOT EXISTS ix_tickets_created_at
    ON tickets (created_at DESC);

-- Tag array filtering (overlap / containment queries)
CREATE INDEX IF NOT EXISTS ix_tickets_tags
    ON tickets USING GIN (tags);

-- Full-text search
CREATE INDEX IF NOT EXISTS ix_tickets_search_vector
    ON tickets USING GIN (search_vector);
