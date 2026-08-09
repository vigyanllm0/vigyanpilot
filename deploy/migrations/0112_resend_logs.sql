-- Rate limiting table for resend-verification endpoint
-- Max 5 resends per email per 24 hours
CREATE TABLE IF NOT EXISTS resend_logs (
    id SERIAL PRIMARY KEY,
    email TEXT NOT NULL,
    ip_address TEXT DEFAULT '0.0.0.0',
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_resend_logs_email ON resend_logs(email);
CREATE INDEX IF NOT EXISTS idx_resend_logs_created ON resend_logs(created_at);
