-- Speeds up range queries by time
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_indexes
    WHERE schemaname='analytics' AND indexname='idx_events_effective_time'
  ) THEN
    EXECUTE 'CREATE INDEX idx_events_effective_time
             ON analytics.data_events(effective_time)';
  END IF;
END$$;

-- Speeds up code breakdowns (GROUP BY code_system, code)
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_indexes
    WHERE schemaname='analytics' AND indexname='idx_events_code_system_code'
  ) THEN
    EXECUTE 'CREATE INDEX idx_events_code_system_code
             ON analytics.data_events(code_system, code)';
  END IF;
END$$;

-- Optional: covers many verifier lookups that combine (code_system, code, effective_time)
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_indexes
    WHERE schemaname='analytics' AND indexname='idx_events_code_time'
  ) THEN
    EXECUTE 'CREATE INDEX idx_events_code_time
             ON analytics.data_events(code_system, code, effective_time)';
  END IF;
END$$;
