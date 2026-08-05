-- Database migration: Add indexes for common clip queries
-- This script optimizes the most common queries on the clips table
-- Safe to run: Non-blocking, can execute while database is live

-- 1. Index on status (common filter: pending, approved, rejected, deleted)
CREATE INDEX IF NOT EXISTS clips_status_idx
ON clips (status)
WHERE status IN ('pending', 'approved', 'rejected');

-- 2. Index on created_at (common sort: recent clips)
CREATE INDEX IF NOT EXISTS clips_created_at_idx
ON clips (created_at DESC);

-- 3. Composite index: streamer_id + status
-- Used by: get_pending_clips(), check_clips_generated(), get_clips()
-- Query example: SELECT * FROM clips WHERE streamer_id = ? AND status = ?
CREATE INDEX IF NOT EXISTS clips_streamer_status_idx
ON clips (streamer_id, status);

-- 4. Composite index: streamer_id + created_at
-- Used by: get_clips(), get_recent_clips()
-- Query example: SELECT * FROM clips WHERE streamer_id = ? ORDER BY created_at DESC
CREATE INDEX IF NOT EXISTS clips_streamer_created_idx
ON clips (streamer_id, created_at DESC);

-- 5. Composite index: status + created_at
-- Used by: get_recent_clips(), filtering by status and date
-- Query example: SELECT * FROM clips WHERE status = ? ORDER BY created_at DESC
CREATE INDEX IF NOT EXISTS clips_status_created_idx
ON clips (status, created_at DESC)
WHERE status IN ('pending', 'approved', 'rejected');

-- 6. Index on export_status
-- Used by: tracking clip exports, finding queued exports
-- Query example: SELECT * FROM clips WHERE export_status = 'queued'
CREATE INDEX IF NOT EXISTS clips_export_status_idx
ON clips (export_status)
WHERE export_status IS NOT NULL;

-- 7. Index on is_public + created_at
-- Used by: public clip feed queries
-- Query example: SELECT * FROM clips WHERE is_public = true ORDER BY created_at DESC
CREATE INDEX IF NOT EXISTS clips_public_created_idx
ON clips (is_public, created_at DESC)
WHERE is_public = true;

-- Performance verification queries:
-- Check index usage:
-- SELECT schemaname, tablename, indexname, idx_scan, idx_tup_read, idx_tup_fetch
-- FROM pg_stat_user_indexes
-- WHERE tablename = 'clips';
--
-- Check index size:
-- SELECT indexname, pg_size_pretty(pg_relation_size(indexrelid)) as index_size
-- FROM pg_stat_user_indexes
-- WHERE tablename = 'clips';
