CREATE MATERIALIZED VIEW IF NOT EXISTS analytics.mv_critical_labs AS
SELECT
  lr.person_id,
  lr.observed_at::timestamptz AS t_utc,
  lr.loinc_code,
  COALESCE(lr.test_name, r.metric_name) AS metric_name,
  lr.value_num,
  lr.unit,
  r.low_critical,
  r.high_critical,
  CASE
    WHEN r.low_critical IS NOT NULL AND lr.value_num < r.low_critical THEN 'low_critical'
    WHEN r.high_critical IS NOT NULL AND lr.value_num > r.high_critical THEN 'high_critical'
    ELSE NULL
  END AS critical_flag
FROM clinical.lab_result lr
LEFT JOIN ref.loinc_critical_ranges r
  ON r.loinc_code = lr.loinc_code;

CREATE INDEX IF NOT EXISTS idx_mv_crit_person_time
  ON analytics.mv_critical_labs(person_id, t_utc DESC);

CREATE OR REPLACE FUNCTION analytics.refresh_critical_labs()
RETURNS void LANGUAGE plpgsql AS $$
BEGIN
  REFRESH MATERIALIZED VIEW CONCURRENTLY analytics.mv_critical_labs;
EXCEPTION WHEN undefined_table THEN
  REFRESH MATERIALIZED VIEW analytics.mv_critical_labs;
END$$;
