-- Migration 002: analysis_session + session_event tables
-- Apply: psql $DATABASE_URL -f migrations/002_sessions.sql

-- Persistent session store (survives process restarts)
CREATE TABLE IF NOT EXISTS analysis_session (
    session_id    TEXT         PRIMARY KEY,
    project_id    TEXT,
    analysis_type TEXT,
    status        TEXT         NOT NULL DEFAULT 'pending',
    input_text    TEXT,
    result        JSONB,
    error         TEXT,
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_session_status ON analysis_session(status);
CREATE INDEX IF NOT EXISTS idx_session_project ON analysis_session(project_id);

-- Append-only event log per session (for replay and history audit)
CREATE TABLE IF NOT EXISTS session_event (
    id            BIGSERIAL    PRIMARY KEY,
    session_id    TEXT         NOT NULL REFERENCES analysis_session(session_id) ON DELETE CASCADE,
    event_type    TEXT         NOT NULL,   -- 'progress' | 'tool_start' | 'approval_required' | 'complete' | 'error' | ...
    payload       JSONB        NOT NULL DEFAULT '{}',
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_session_event_sid ON session_event(session_id, created_at);
