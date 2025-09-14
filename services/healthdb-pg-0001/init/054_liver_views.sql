-- services/healthdb-pg-0001/init/054_liver_views.sql
-- Latest liver labs per person (most recent per code pivoted to columns)
CREATE OR REPLACE VIEW analytics.v_liver_latest AS
WITH ranked AS (
  SELECT
    person_id, code, value_num, unit, effective_time,
    ROW_NUMBER() OVER (PARTITION BY person_id, code ORDER BY effective_time DESC) AS rn
  FROM analytics.data_events
  WHERE code_system='LOINC'
    AND code IN ('1742-6','1920-8','6768-6','2324-2','1975-2','1968-7','1751-7')
)
SELECT
  person_id,
  MAX(CASE WHEN code='1742-6' THEN value_num END) FILTER (WHERE rn=1) AS alt_uL,
  MAX(CASE WHEN code='1920-8' THEN value_num END) FILTER (WHERE rn=1) AS ast_uL,
  MAX(CASE WHEN code='6768-6' THEN value_num END) FILTER (WHERE rn=1) AS alp_uL,
  MAX(CASE WHEN code='2324-2' THEN value_num END) FILTER (WHERE rn=1) AS ggt_uL,
  MAX(CASE WHEN code='1975-2' THEN value_num END) FILTER (WHERE rn=1) AS bili_total_mgdl,
  MAX(CASE WHEN code='1968-7' THEN value_num END) FILTER (WHERE rn=1) AS bili_direct_mgdl,
  MAX(CASE WHEN code='1751-7' THEN value_num END) FILTER (WHERE rn=1) AS albumin_gdl,
  MAX(effective_time) FILTER (WHERE rn=1) AS updated_at
FROM ranked
GROUP BY person_id
ORDER BY updated_at DESC NULLS LAST;

-- Daily medians (or mins for bilirubin) per person/day for liver labs
CREATE MATERIALIZED VIEW IF NOT EXISTS analytics.mv_liver_daily AS
SELECT
  person_id,
  (effective_time AT TIME ZONE 'UTC')::date AS day,
  -- choose aggregation suitable for each lab (you can change these)
  PERCENTILE_DISC(0.5) WITHIN GROUP (ORDER BY CASE WHEN code='1742-6' THEN value_num END) AS alt_p50,
  PERCENTILE_DISC(0.5) WITHIN GROUP (ORDER BY CASE WHEN code='1920-8' THEN value_num END) AS ast_p50,
  PERCENTILE_DISC(0.5) WITHIN GROUP (ORDER BY CASE WHEN code='6768-6' THEN value_num END) AS alp_p50,
  PERCENTILE_DISC(0.5) WITHIN GROUP (ORDER BY CASE WHEN code='2324-2' THEN value_num END) AS ggt_p50,
  MAX(CASE WHEN code='1975-2' THEN value_num END) AS bili_total_max,    -- often tracked as a max in a day
  MAX(CASE WHEN code='1968-7' THEN value_num END) AS bili_direct_max,
  PERCENTILE_DISC(0.5) WITHIN GROUP (ORDER BY CASE WHEN code='1751-7' THEN value_num END) AS albumin_p50
FROM analytics.data_events
WHERE code_system='LOINC'
  AND code IN ('1742-6','1920-8','6768-6','2324-2','1975-2','1968-7','1751-7')
  AND value_num IS NOT NULL
GROUP BY 1,2
ORDER BY day DESC;

CREATE INDEX IF NOT EXISTS idx_mv_liver_daily_day ON analytics.mv_liver_daily(day);
