-- =============================================================================
-- Ticket workflow status
-- PostgreSQL required
--
-- Adds a `status` column reflecting the incident's workflow state
-- (unassigned / in_progress / resolved). Existing rows default to
-- 'unassigned'; see 004_backfill_ticket_status_from_resolution.sql for an
-- optional, manually-run backfill based on resolution_summary content.
--
-- Example:
--   psql -U postgres -d pyTickets -f database/003_add_ticket_status.sql
-- =============================================================================

\connect "pyTickets"

ALTER TABLE tickets
    ADD COLUMN IF NOT EXISTS status VARCHAR(20) NOT NULL DEFAULT 'unassigned'
        CHECK (status IN ('unassigned', 'in_progress', 'resolved'));

CREATE INDEX IF NOT EXISTS ix_tickets_status
    ON tickets (status);
