-- =============================================================
-- 001: Required Extensions
-- =============================================================

CREATE EXTENSION IF NOT EXISTS pgcrypto;          -- gen_random_uuid(), crypt()
CREATE EXTENSION IF NOT EXISTS pg_stat_statements; -- Query performance monitoring
CREATE EXTENSION IF NOT EXISTS pg_trgm;           -- Trigram fuzzy text search (for logs)
