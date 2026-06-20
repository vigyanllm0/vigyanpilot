-- Fix academic_claims: add missing columns that Python code expects
ALTER TABLE IF EXISTS academic_claims ADD COLUMN IF NOT EXISTS use_case TEXT;
ALTER TABLE IF EXISTS academic_claims ADD COLUMN IF NOT EXISTS email_edu VARCHAR(320);
ALTER TABLE IF EXISTS academic_claims ADD COLUMN IF NOT EXISTS document_path TEXT;
ALTER TABLE IF EXISTS academic_claims ADD COLUMN IF NOT EXISTS reviewed_by BIGINT REFERENCES users(id);
ALTER TABLE IF EXISTS academic_claims ADD COLUMN IF NOT EXISTS reviewed_at TIMESTAMPTZ;
ALTER TABLE IF EXISTS academic_claims ADD COLUMN IF NOT EXISTS proof_method VARCHAR(32) DEFAULT 'email';
