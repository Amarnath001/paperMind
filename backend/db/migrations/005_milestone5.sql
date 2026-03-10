-- Milestone 5 schema changes: paper summaries, topics, and clustering

-- NOTE: This migration is intended for databases that were already
-- initialized before backend/db/schema.sql was updated for Milestone 5.
-- For a clean local reset you can alternatively run:
--   docker compose down -v
--   docker compose up --build


-- 1) Add summary column to papers if it does not already exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM   information_schema.columns
        WHERE  table_name  = 'papers'
        AND    column_name = 'summary'
    ) THEN
        ALTER TABLE papers ADD COLUMN summary TEXT;
    END IF;
END;
$$;


-- 2) Add topics column to papers if it does not already exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM   information_schema.columns
        WHERE  table_name  = 'papers'
        AND    column_name = 'topics'
    ) THEN
        ALTER TABLE papers ADD COLUMN topics TEXT[];
    END IF;
END;
$$;


-- 3) Add cluster_id column to papers if it does not already exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM   information_schema.columns
        WHERE  table_name  = 'papers'
        AND    column_name = 'cluster_id'
    ) THEN
        ALTER TABLE papers ADD COLUMN cluster_id INTEGER;
    END IF;
END;
$$;

