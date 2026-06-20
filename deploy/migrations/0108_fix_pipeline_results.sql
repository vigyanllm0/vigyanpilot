-- Add missing phase column to pipeline_results (referenced by tasks.py INSERT)
ALTER TABLE IF EXISTS pipeline_results ADD COLUMN IF NOT EXISTS phase VARCHAR(1);
