-- Migration: Create agent_tokens table
-- This table stores long-lived tokens for autonomous clipping agents
-- Each streamer can have one active token at a time

CREATE TABLE IF NOT EXISTS agent_tokens (
    id SERIAL PRIMARY KEY,
    streamer_id INTEGER NOT NULL REFERENCES streamers(id) ON DELETE CASCADE,
    token_hash VARCHAR NOT NULL UNIQUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    revoked_at TIMESTAMP WITH TIME ZONE,
    INDEX idx_agent_tokens_streamer_id (streamer_id),
    INDEX idx_agent_tokens_token_hash (token_hash),
    INDEX idx_agent_tokens_expires_at (expires_at)
);

-- Index for querying active tokens
CREATE INDEX IF NOT EXISTS idx_agent_tokens_active
ON agent_tokens (streamer_id)
WHERE revoked_at IS NULL;
