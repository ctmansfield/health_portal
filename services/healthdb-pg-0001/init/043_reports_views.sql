-- 043_reports_views.sql
-- Materialized and regular views to support dashboards and reporting

-- Hour-of-day HR pattern (median & p90) for recent 60 days
CREATE MATERIALIZED VIEW IF NOT EXISTS analytics.mv_hr_hourly AS
WITH pts AS (
  SELECT person_id,
         (effective_time AT TIME ZONE 'UTC')::date AS day,
         EXTRACT(hour FROM effective_time AT TIME ZONE 'UTC')::int AS hour,
         value_num AS hr
  FROM analytics.data_events
  WHERE code_system='LOINC' AND code='8867-4' AND effective_time >= now() - interval '60 days'
)
SELECT person_id, hour,
       percentile_disc(0.5) WITHIN GROUP (ORDER BY hr) AS hr_median,
       percentile_disc(0.9) WITHIN GROUP (ORDER BY hr) AS hr_p90,
       count(*) AS n
FROM pts
GROUP BY person_id, hour
ORDER BY person_id, hour;

CREATE INDEX IF NOT EXISTS idx_mv_hr_hourly_person_hour ON analytics.mv_hr_hourly(person_id, hour);

-- Daily SpO2 percentiles (p10/p50/p90) for recent 120 days
CREATE MATERIALIZED VIEW IF NOT EXISTS analytics.mv_spo2_daily_pct AS
WITH src AS (
  SELECT person_id, (effective_time AT TIME ZONE 'UTC')::date AS day, value_num AS spo2
  FROM analytics.data_events
  WHERE code_system='LOINC' AND code='59408-5' AND effective_time >= now() - interval '120 days'
)
SELECT person_id, day,
       percentile_disc(0.1) WITHIN GROUP (ORDER BY spo2) AS p10,
       percentile_disc(0.5) WITHIN GROUP (ORDER BY spo2) AS p50,
       percentile_disc(0.9) WITHIN GROUP (ORDER BY spo2) AS p90,
       count(*) AS n
FROM src
GROUP BY person_id, day
ORDER BY day DESC;

CREATE INDEX IF NOT EXISTS idx_mv_spo2_daily_pct_person_day ON analytics.mv_spo2_daily_pct(person_id, day);

-- AI findings summary view (counts by level in recent 30 days)
CREATE OR REPLACE VIEW analytics.v_ai_summary AS
SELECT person_id,
       finding_time::date AS day,
       level,
       count(*) AS cnt
FROM analytics.ai_findings
WHERE finding_time >= now() - interval '30 days'
GROUP BY person_id, day, level
ORDER BY person_id, day DESC;

-- Recent events joined with the latest finding for the same person (read-only view)
CREATE OR REPLACE VIEW analytics.v_recent_events_with_findings AS
SELECT e.person_id, e.source, e.kind, e.code_system, e.code, e.value_num, e.unit, e.effective_time, e.meta,
       f.metric AS finding_metric, f.level AS finding_level, f.score AS finding_score, f.finding_time AS finding_time
FROM analytics.v_events_recent e
LEFT JOIN LATERAL (
  SELECT metric, level, score, finding_time
  FROM analytics.ai_findings f
  WHERE f.person_id = e.person_id
  ORDER BY finding_time DESC
  LIMIT 1
) f ON true
ORDER BY e.effective_time DESC;

-- HR daily z-score over a trailing 21-day window (materialized for dashboard use)
CREATE MATERIALIZED VIEW IF NOT EXISTS analytics.mv_hr_daily_zscore AS
WITH daily AS (
  SELECT person_id, day, hr_median
  FROM analytics.mv_daily_vitals
)
SELECT person_id, day,
       hr_median,
       (hr_median - avg(hr_median) OVER w) / NULLIF(stddev_pop(hr_median) OVER w, 0) AS zscore
FROM daily
WINDOW w AS (PARTITION BY person_id ORDER BY day ROWS BETWEEN 20 PRECEDING AND CURRENT ROW);

CREATE INDEX IF NOT EXISTS idx_mv_hr_daily_zscore_person_day ON analytics.mv_hr_daily_zscore(person_id, day);
