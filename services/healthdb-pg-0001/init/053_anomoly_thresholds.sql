-- One row per metric (LOINC code). NULL min/max means "no bound".
CREATE TABLE IF NOT EXISTS analytics.anomaly_thresholds (
  code          text PRIMARY KEY,                 -- e.g., 8867-4, 59408-5
  min_val       double precision,
  max_val       double precision,
  reason        text DEFAULT 'out of configured range',
  enabled       boolean NOT NULL DEFAULT true,
  updated_at    timestamptz NOT NULL DEFAULT now()
);

-- Seed common vitals (tune later)
INSERT INTO analytics.anomaly_thresholds (code, min_val, max_val, reason)
VALUES
  ('8867-4', 20, 220, 'Heart rate out of range (bpm)'),
  ('59408-5', 0.5, 1.0, 'SpO2 outside 50%–100% (ratio 0–1)'),
  ('29463-7', 25, 500, 'Weight suspicious (kg)')
ON CONFLICT (code) DO NOTHING;
