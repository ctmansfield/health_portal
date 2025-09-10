-- Unique index for analytics.mv_events_daily (enables CONCURRENTLY)
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_indexes
    WHERE schemaname='analytics' AND indexname='ux_mv_events_daily_key'
  ) THEN
    EXECUTE 'CREATE UNIQUE INDEX ux_mv_events_daily_key
             ON analytics.mv_events_daily(person_id, day, code_system, code)';
  END IF;
END$$;

-- Unique index for analytics.mv_vitals_daily_wide (enables CONCURRENTLY)
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_indexes
    WHERE schemaname='analytics' AND indexname='ux_mv_vitals_daily_wide_key'
  ) THEN
    EXECUTE 'CREATE UNIQUE INDEX ux_mv_vitals_daily_wide_key
             ON analytics.mv_vitals_daily_wide(person_id, day)';
  END IF;
END$$;
