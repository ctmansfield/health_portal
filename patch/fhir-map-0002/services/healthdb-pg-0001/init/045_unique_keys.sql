DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_indexes
    WHERE schemaname='analytics' AND indexname='uq_events_person_metric_time'
  ) THEN
    EXECUTE $DDL$
      CREATE UNIQUE INDEX uq_events_person_metric_time
        ON analytics.data_events(person_id, code_system, code, effective_time)
        WHERE value_num IS NOT NULL;
    $DDL$;
  END IF;
END $$;
