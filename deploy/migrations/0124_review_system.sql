-- 0124: Review/Testimonial system
-- Extends feedback_submissions with display fields for public testimonials.
-- Adds has_reviewed flag to users for review prompt gating.

-- Extend feedback_submissions with display fields
ALTER TABLE feedback_submissions ADD COLUMN IF NOT EXISTS name VARCHAR(100) DEFAULT '';
ALTER TABLE feedback_submissions ADD COLUMN IF NOT EXISTS role_label VARCHAR(100) DEFAULT '';
ALTER TABLE feedback_submissions ADD COLUMN IF NOT EXISTS institution VARCHAR(200) DEFAULT '';
ALTER TABLE feedback_submissions ADD COLUMN IF NOT EXISTS is_approved BOOLEAN DEFAULT FALSE;
ALTER TABLE feedback_submissions ADD COLUMN IF NOT EXISTS is_featured BOOLEAN DEFAULT FALSE;
ALTER TABLE feedback_submissions ADD COLUMN IF NOT EXISTS reviewed_at DOUBLE PRECISION;

-- Indexes for fast public display
CREATE INDEX IF NOT EXISTS idx_feedback_approved ON feedback_submissions(is_approved) WHERE is_approved = TRUE;
CREATE INDEX IF NOT EXISTS idx_feedback_featured ON feedback_submissions(is_featured) WHERE is_featured = TRUE;

-- Track review status on users
ALTER TABLE users ADD COLUMN IF NOT EXISTS has_reviewed BOOLEAN DEFAULT FALSE;
