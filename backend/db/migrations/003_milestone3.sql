-- Milestone 3 schema changes: pgvector embeddings on papers and chunks

-- NOTE: This migration is intended for databases that were already
-- initialized before backend/db/schema.sql was updated for Milestone 3.
-- For a clean local reset you can alternatively run:
--   docker compose down -v
--   docker compose up --build


-- 1) Enable the pgvector extension (safe to run repeatedly)
CREATE EXTENSION IF NOT EXISTS vector;


-- 2) Add embedding column to papers if it does not already exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM   information_schema.columns
        WHERE  table_name  = 'papers'
        AND    column_name = 'embedding'
    ) THEN
        ALTER TABLE papers ADD COLUMN embedding vector(384);
    END IF;
END;
$$;


-- 3) Add embedding column to chunks if it does not already exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM   information_schema.columns
        WHERE  table_name  = 'chunks'
        AND    column_name = 'embedding'
    ) THEN
        ALTER TABLE chunks ADD COLUMN embedding vector(384);
    END IF;
END;
$$;


-- 4) Create ivfflat index on papers.embedding (cosine distance)
--    ivfflat requires at least one row to build; we skip if the table is empty.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM   pg_indexes
        WHERE  tablename  = 'papers'
        AND    indexname  = 'idx_papers_embedding'
    ) THEN
        IF EXISTS (SELECT 1 FROM papers LIMIT 1) THEN
            EXECUTE 'CREATE INDEX idx_papers_embedding
                     ON papers USING ivfflat (embedding vector_cosine_ops)
                     WITH (lists = 100)';
        ELSE
            RAISE NOTICE 'Skipping idx_papers_embedding: papers table is empty. '
                         'Re-run this migration after inserting rows, or create '
                         'the index manually.';
        END IF;
    END IF;
END;
$$;


-- 5) Create ivfflat index on chunks.embedding (cosine distance)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM   pg_indexes
        WHERE  tablename  = 'chunks'
        AND    indexname  = 'idx_chunks_embedding'
    ) THEN
        IF EXISTS (SELECT 1 FROM chunks LIMIT 1) THEN
            EXECUTE 'CREATE INDEX idx_chunks_embedding
                     ON chunks USING ivfflat (embedding vector_cosine_ops)
                     WITH (lists = 100)';
        ELSE
            RAISE NOTICE 'Skipping idx_chunks_embedding: chunks table is empty. '
                         'Re-run this migration after inserting rows, or create '
                         'the index manually.';
        END IF;
    END IF;
END;
$$;
