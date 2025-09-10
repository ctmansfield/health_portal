-- Flag values that look physiologically odd; tweak thresholds later
CREATE OR REPLACE VIEW analytics.v_vitals_anomalies AS
SELECT
  person_id,
  effective_time,
  code_system,
  code,
  value_num,
  CASE
    WHEN code='8867-4' AND (value_num < 20 OR value_num > 220)
      THEN 'Heart rate out of range'
    WHEN code='59408-5' AND (value_num < 0.5 OR value_num > 1.0)
      THEN 'SpO2 outside 50%-100%'
    WHEN code='29463-7' AND (value_num < 25 OR value_num > 500)
      THEN 'Weight suspicious (kg)'
  END AS reason
FROM analytics.data_events
WHERE code_system='LOINC'
  AND (
    (code='8867-4' AND (value_num < 20 OR value_num > 220)) OR
    (code='59408-5' AND (value_num < 0.5 OR value_num > 1.0)) OR
    (code='29463-7' AND (value_num < 25  OR value_num > 500))
  )
ORDER BY effective_time DESC;
