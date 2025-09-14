-- Add a unique index on person_id and day for mv_liver_daily to enable concurrent refresh
CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_liver_daily_person_day ON analytics.mv_liver_daily (person_id, day);

-- Then refresh materialized view concurrently
REFRESH MATERIALIZED VIEW CONCURRENTLY analytics.mv_liver_daily;
