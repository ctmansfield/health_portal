CREATE MATERIALIZED VIEW IF NOT EXISTS analytics.mv_daily_vitals AS
WITH d AS (
  SELECT person_id,
         effective_time::date AS day,
         CASE WHEN code_system='LOINC' AND code='8867-4' THEN value_num END AS hr,
         CASE WHEN code_system='LOINC' AND code='59408-5' THEN value_num END AS spo2
  FROM analytics.data_events
  WHERE effective_time >= now() - interval '120 days'
)
SELECT person_id,
       day::date,
       percentile_disc(0.5) within group (order by hr)   AS hr_median,
       min(spo2)                                         AS spo2_min
FROM d
GROUP BY 1,2
ORDER BY 2 DESC, 1;

CREATE INDEX IF NOT EXISTS idx_mv_daily_vitals_day ON analytics.mv_daily_vitals(day);

-- Unique index required for CONCURRENTLY
CREATE UNIQUE INDEX IF NOT EXISTS uq_mv_daily_vitals
  ON analytics.mv_daily_vitals(person_id, day);
