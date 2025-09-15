\set ON_ERROR_STOP on

DO $merge$
DECLARE
  has_source       boolean;
  has_code_display boolean;
BEGIN
  SELECT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema='analytics' AND table_name='data_events' AND column_name='source'
  ) INTO has_source;

  SELECT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema='analytics' AND table_name='data_events' AND column_name='code_display'
  ) INTO has_code_display;

  IF has_source AND has_code_display THEN
    INSERT INTO analytics.data_events
      (person_id, source, code_system, code, code_display, value_num, unit, effective_time, meta)
    SELECT
      s.person_id,
      'portal'::text AS source,
      s.code_system,
      s.code,
      s.test_name    AS code_display,
      s.value_num,
      s.unit,
      s.effective_time,
      COALESCE(NULLIF(ir.meta::text,''), '{}')::jsonb
        || jsonb_build_object('run_id', s.run_id, 'source_file', ir.source_file, 'importer', 'portal_ingest_vfix2')
    FROM ingest_portal.stg_portal_labs s
    JOIN ingest_portal.import_run ir USING (run_id)
    WHERE s.run_id = :'RUN_ID'::uuid
    ON CONFLICT DO NOTHING;

  ELSIF has_source THEN
    INSERT INTO analytics.data_events
      (person_id, source, code_system, code, value_num, unit, effective_time, meta)
    SELECT
      s.person_id,
      'portal'::text AS source,
      s.code_system,
      s.code,
      s.value_num,
      s.unit,
      s.effective_time,
      jsonb_build_object('run_id', s.run_id, 'source_file', ir.source_file, 'importer', 'portal_ingest_vfix2')
    FROM ingest_portal.stg_portal_labs s
    JOIN ingest_portal.import_run ir USING (run_id)
    WHERE s.run_id = :'RUN_ID'::uuid
    ON CONFLICT DO NOTHING;

  ELSE
    INSERT INTO analytics.data_events
      (person_id, code_system, code, value_num, unit, effective_time, meta)
    SELECT
      s.person_id,
      s.code_system,
      s.code,
      s.value_num,
      s.unit,
      s.effective_time,
      jsonb_build_object('run_id', s.run_id, 'source_file', ir.source_file, 'source', 'portal', 'importer', 'portal_ingest_vfix2')
    FROM ingest_portal.stg_portal_labs s
    JOIN ingest_portal.import_run ir USING (run_id)
    WHERE s.run_id = :'RUN_ID'::uuid
    ON CONFLICT DO NOTHING;
  END IF;
END
$merge$;
