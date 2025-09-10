-- Replaces previous hard-coded thresholds with table-driven logic
CREATE OR REPLACE VIEW analytics.v_vitals_anomalies AS
SELECT
  e.person_id,
  e.effective_time,
  e.code_system,
  e.code,
  e.value_num,
  t.reason
FROM analytics.data_events e
JOIN analytics.anomaly_thresholds t
  ON t.code = e.code
 AND t.enabled
WHERE e.code_system = 'LOINC'
  AND e.value_num IS NOT NULL
  AND (
        (t.min_val IS NOT NULL AND e.value_num < t.min_val) OR
        (t.max_val IS NOT NULL AND e.value_num > t.max_val)
      )
ORDER BY e.effective_time DESC;
