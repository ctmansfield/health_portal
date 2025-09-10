-- Recent events (last 14 days)
CREATE OR REPLACE VIEW analytics.v_events_recent AS
SELECT person_id, source, kind, code_system, code, value_num, unit, effective_time, meta
FROM analytics.data_events
WHERE effective_time >= now() - interval '14 days'
ORDER BY effective_time DESC;

-- Daily rollups per code/day
CREATE MATERIALIZED VIEW IF NOT EXISTS analytics.mv_events_daily AS
SELECT
  person_id,
  (effective_time AT TIME ZONE 'UTC')::date AS day,
  code_system,
  code,
  count(*)         AS n,
  avg(value_num)   AS avg_val,
  min(value_num)   AS min_val,
  max(value_num)   AS max_val
FROM analytics.data_events
GROUP BY 1,2,3,4
ORDER BY 2 DESC, 1, 3, 4;

CREATE INDEX IF NOT EXISTS idx_mv_events_daily_day    ON analytics.mv_events_daily(day);
CREATE INDEX IF NOT EXISTS idx_mv_events_daily_person ON analytics.mv_events_daily(person_id);

-- Daily vitals wide (median HR, min SpO2). Keep as-is; we’ll avoid it in the verifier.
CREATE MATERIALIZED VIEW IF NOT EXISTS analytics.mv_vitals_daily_wide AS
WITH src AS (
  SELECT
    person_id,
    (effective_time AT TIME ZONE 'UTC')::date AS day,
    CASE WHEN code_system='LOINC' AND code='8867-4' THEN value_num END AS hr,
    CASE WHEN code_system='LOINC' AND code='59408-5' THEN value_num END AS spo2
  FROM analytics.data_events
)
SELECT
  person_id,
  day,
  percentile_disc(0.5) WITHIN GROUP (ORDER BY hr) AS hr_median,
  min(spo2) AS spo2_min
FROM src
GROUP BY 1,2
ORDER BY day DESC;

CREATE INDEX IF NOT EXISTS idx_mv_vitals_daily_wide_day ON analytics.mv_vitals_daily_wide(day);

-- Latest vitals snapshot per person (fast via DISTINCT ON + partial indexes)
CREATE OR REPLACE VIEW analytics.v_vitals_latest AS
WITH
hr AS (
  SELECT DISTINCT ON (person_id)
         person_id, value_num::float AS hr_latest, effective_time AS hr_time
  FROM analytics.data_events
  WHERE code_system='LOINC' AND code='8867-4' AND value_num IS NOT NULL
  ORDER BY person_id, effective_time DESC
),
spo2 AS (
  SELECT DISTINCT ON (person_id)
         person_id, value_num::float AS spo2_latest, effective_time AS spo2_time
  FROM analytics.data_events
  WHERE code_system='LOINC' AND code='59408-5' AND value_num IS NOT NULL
  ORDER BY person_id, effective_time DESC
)
SELECT
  COALESCE(hr.person_id, spo2.person_id) AS person_id,
  hr.hr_latest,
  spo2.spo2_latest,
  GREATEST(COALESCE(hr.hr_time, '-infinity'), COALESCE(spo2.spo2_time, '-infinity')) AS updated_at
FROM hr
FULL OUTER JOIN spo2 USING (person_id);
