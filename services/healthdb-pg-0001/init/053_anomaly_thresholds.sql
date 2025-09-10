-- Create table of configurable anomaly thresholds
CREATE SCHEMA IF NOT EXISTS analytics;

CREATE TABLE IF NOT EXISTS analytics.anomaly_thresholds (
  code        text PRIMARY KEY,               -- LOINC code, e.g., 8867-4
  min_val     double precision,
  max_val     double precision,
  reason      text DEFAULT 'out of configured range',
  enabled     boolean NOT NULL DEFAULT true,
  updated_at  timestamptz NOT NULL DEFAULT now()
);

-- Seed a few common metrics (idempotent)
INSERT INTO analytics.anomaly_thresholds (code, min_val, max_val, reason)
VALUES
  ('8867-4', 20, 220, 'Heart rate out of range (bpm)'),
  ('59408-5', 0.5, 1.0, 'SpO2 outside 50%–100% (ratio 0–1)'),
  ('29463-7', 25, 500, 'Weight suspicious (kg)')
ON CONFLICT (code) DO NOTHING;
