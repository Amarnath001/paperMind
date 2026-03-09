-- Milestone 2 schema changes: jobs, chunks, and extended paper statuses

-- NOTE: This migration is intended for databases that were already
-- initialized before backend/db/schema.sql was updated for Milestone 2.
-- For a clean local reset you can alternatively run:
--   docker compose down -v
--   docker compose up --build

-- 1) Extend papers.status to support 'failed'
DO $$
BEGIN
    -- Attempt to drop a known constraint name if it exists.
    -- If your database uses a different auto-generated name,
    -- you may need to adjust this statement.
    IF EXISTS (
        SELECT 1
        FROM   pg_constraint
        WHERE  conrelid = 'papers'::regclass
        AND    conname = 'papers_status_check'
    ) THEN
        ALTER TABLE papers DROP CONSTRAINT papers_status_check;
    END IF;
EXCEPTION
    WHEN undefined_table THEN
        -- Table does not exist yet; nothing to do.
        NULL;
END;
$$;

-- Add the new CHECK constraint allowing the extended set of statuses.
ALTER TABLE papers
    ADD CONSTRAINT papers_status_check
    CHECK (status IN ('uploaded','processing','ready','failed'));


-- 2) Jobs table
CREATE TABLE IF NOT EXISTS jobs (
    id UUID PRIMARY KEY,
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    paper_id UUID REFERENCES papers(id) ON DELETE CASCADE,
    type TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('queued','running','completed','failed')),
    progress INTEGER NOT NULL DEFAULT 0,
    error TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_jobs_workspace_id
    ON jobs (workspace_id);

CREATE INDEX IF NOT EXISTS idx_jobs_paper_id
    ON jobs (paper_id);


-- 3) Chunks table
CREATE TABLE IF NOT EXISTS chunks (
    id UUID PRIMARY KEY,
    paper_id UUID NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    text TEXT NOT NULL,
    token_count INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_chunks_paper_id
    ON chunks (paper_id);

