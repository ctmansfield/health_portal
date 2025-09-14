-- services/healthdb-pg-0001/init/055_liver_thresholds.sql
INSERT INTO analytics.anomaly_thresholds (code, min_val, max_val, reason, enabled)
VALUES
  ('1742-6', 0, 55,  'ALT high', TRUE),
  ('1920-8', 0, 40,  'AST high', TRUE),
  ('6768-6', 30, 120,'ALP out of range', TRUE),
  ('2324-2', 0, 60,  'GGT high', TRUE),
  ('1975-2', 0, 1.3, 'Bilirubin total high', TRUE),
  ('1968-7', 0, 0.3, 'Bilirubin direct high', TRUE),
  ('1751-7', 3.2, 5.0, 'Albumin low/high', TRUE)
ON CONFLICT (code) DO NOTHING;
