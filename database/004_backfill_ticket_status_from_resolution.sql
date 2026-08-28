-- =============================================================================
-- OPTIONAL, MANUAL backfill: ticket status from resolution_summary
-- PostgreSQL required
--
-- This script is NOT run automatically by any migration step and is not
-- part of 003_add_ticket_status.sql. Run it yourself, when you choose to.
-- Only touches rows where status is still unset (NULL or empty), so it's
-- safe to re-run without clobbering statuses that have already been
-- backfilled or set some other way.
--
-- Heuristic: non-empty resolution_summary -> resolved, fallback -> unassigned.
-- Note: this cannot distinguish `in_progress` from `resolved` — any ticket
-- with resolution text is classified as resolved.
--
-- Example:
--   psql -U postgres -d pyTickets -f database/004_backfill_ticket_status_from_resolution.sql
-- =============================================================================

\connect "pyTickets"

UPDATE tickets
SET status = CASE
    WHEN resolution_summary IS NOT NULL AND resolution_summary <> '' THEN 'resolved'
    ELSE 'unassigned'
END
WHERE status IS NULL OR status = '';
