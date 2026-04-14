-- Migration: create audit_log table for ISO 26262 traceability
-- Apply with: psql $DATABASE_URL -f migrations/001_audit_log.sql

CREATE TABLE IF NOT EXISTS audit_log (
    id           BIGSERIAL    PRIMARY KEY,
    thread_id    TEXT         NOT NULL,
    stage        TEXT         NOT NULL,
    engineer_id  TEXT         NOT NULL,
    decision     TEXT         NOT NULL,          -- 'approved' | 'rejected'
    original_data JSONB,
    modified_data JSONB,
    timestamp    TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_thread ON audit_log(thread_id);
CREATE INDEX IF NOT EXISTS idx_audit_stage  ON audit_log(stage);
