-- Latest BP per person (systolic/diastolic)
CREATE OR REPLACE VIEW analytics.v_bp_latest AS
WITH ranked AS (
  SELECT
    person_id,
    code,
    value_num,
    effective_time,
    ROW_NUMBER() OVER (PARTITION BY person_id, code ORDER BY effective_time DESC) AS rn
  FROM analytics.data_events
  WHERE code_system='LOINC' AND code IN ('8480-6','8462-4') AND value_num IS NOT NULL
)
SELECT
  s.person_id,
  s.value_num AS systolic_mmHg,
  d.value_num AS diastolic_mmHg,
  GREATEST(s.effective_time, d.effective_time) AS updated_at
FROM ranked s
LEFT JOIN ranked d
  ON d.person_id=s.person_id AND d.code='8462-4' AND d.rn=1
WHERE s.code='8480-6' AND s.rn=1;

-- Weight daily median (kg)
CREATE MATERIALIZED VIEW IF NOT EXISTS analytics.mv_weight_daily AS
SELECT
  person_id,
  (effective_time AT TIME ZONE 'UTC')::date AS day,
  percentile_disc(0.5) WITHIN GROUP (ORDER BY value_num) AS weight_median_kg
FROM analytics.data_events
WHERE code_system='LOINC' AND code='29463-7' AND value_num IS NOT NULL
GROUP BY 1,2
ORDER BY day DESC;

CREATE INDEX IF NOT EXISTS idx_mv_weight_daily_day ON analytics.mv_weight_daily(day);
