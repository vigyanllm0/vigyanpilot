-- =============================================================
-- 007: Table Partitioning (for high-growth tables)
-- =============================================================

-- Drop the non-partitioned system_events and recreate as partitioned
DROP TABLE IF EXISTS system_events CASCADE;

CREATE TABLE system_events (
    id              BIGSERIAL,
    severity        event_severity NOT NULL,
    module          VARCHAR(128) NOT NULL,
    message         TEXT NOT NULL,
    context         JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (id, created_at)
) PARTITION BY RANGE (created_at);

-- Partitions: June 2026 through December 2026 + Q1 2027
CREATE TABLE system_events_2026_06 PARTITION OF system_events
    FOR VALUES FROM ('2026-06-01') TO ('2026-07-01');
CREATE TABLE system_events_2026_07 PARTITION OF system_events
    FOR VALUES FROM ('2026-07-01') TO ('2026-08-01');
CREATE TABLE system_events_2026_08 PARTITION OF system_events
    FOR VALUES FROM ('2026-08-01') TO ('2026-09-01');
CREATE TABLE system_events_2026_09 PARTITION OF system_events
    FOR VALUES FROM ('2026-09-01') TO ('2026-10-01');
CREATE TABLE system_events_2026_10 PARTITION OF system_events
    FOR VALUES FROM ('2026-10-01') TO ('2026-11-01');
CREATE TABLE system_events_2026_11 PARTITION OF system_events
    FOR VALUES FROM ('2026-11-01') TO ('2026-12-01');
CREATE TABLE system_events_2026_12 PARTITION OF system_events
    FOR VALUES FROM ('2026-12-01') TO ('2027-01-01');
CREATE TABLE system_events_2027_01 PARTITION OF system_events
    FOR VALUES FROM ('2027-01-01') TO ('2027-02-01');
CREATE TABLE system_events_2027_02 PARTITION OF system_events
    FOR VALUES FROM ('2027-02-01') TO ('2027-03-01');
CREATE TABLE system_events_2027_03 PARTITION OF system_events
    FOR VALUES FROM ('2027-03-01') TO ('2027-04-01');
CREATE TABLE system_events_default PARTITION OF system_events DEFAULT;

-- Re-add indexes on partitioned table
CREATE INDEX idx_events_severity ON system_events (severity);
CREATE INDEX idx_events_module ON system_events (module);
CREATE INDEX idx_events_created_at ON system_events (created_at DESC);
CREATE INDEX idx_events_critical ON system_events (created_at DESC)
    WHERE severity IN ('ERROR', 'CRITICAL');

-- -----------------------------------------------------------
-- Monthly partition creation template (run via cron/pg_cron)
-- -----------------------------------------------------------
-- CREATE TABLE system_events_YYYY_MM PARTITION OF system_events
--     FOR VALUES FROM ('YYYY-MM-01') TO ('YYYY-{MM+1}-01');
-- 
-- To retire old data:
-- DROP TABLE system_events_2026_06;  -- Instant, no VACUUM needed
