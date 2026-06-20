CREATE TABLE IF NOT EXISTS system_events (
    id BIGSERIAL PRIMARY KEY,
    severity VARCHAR(20) NOT NULL DEFAULT 'INFO',
    module VARCHAR(100) NOT NULL,
    message TEXT NOT NULL,
    context JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW()
);
