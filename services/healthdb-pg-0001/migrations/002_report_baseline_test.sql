-- 002_report_baseline_test.sql
-- Quick test/assertion migration to verify report baseline objects exist and have expected columns/types.
-- This file is intended to be run manually in CI or staging after applying the up migration.

BEGIN;
SET LOCAL lock_timeout='5s';
SET LOCAL statement_timeout='1min';

-- Check that the view exists and has the expected columns and types
-- We raise exceptions (via the assert pattern) when checks fail.

-- 1) existence check
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.views
    WHERE table_schema = 'analytics' AND table_name = 'report_exec_summary'
  ) THEN
    RAISE EXCEPTION 'View analytics.report_exec_summary not found';
  END IF;
END$$;

-- 2) column names and types
DO $$
DECLARE
  rec RECORD;
  expected_columns CONSTANT text[] := ARRAY['id','title','result','signed_out_at'];
  found_count int;
BEGIN
  SELECT COUNT(*) INTO found_count
  FROM information_schema.columns
  WHERE table_schema = 'analytics' AND table_name = 'report_exec_summary' AND column_name = ANY(expected_columns);
  IF found_count <> array_length(expected_columns,1) THEN
    RAISE EXCEPTION 'report_exec_summary missing expected columns: expected % rows found %', expected_columns, found_count;
  END IF;
END$$;

-- 3) basic type checks (id text, title text, result text, signed_out_at timestamp with time zone)
DO $$
DECLARE
  t_id text;
  t_title text;
  t_result text;
  t_signed text;
BEGIN
  SELECT data_type INTO t_id FROM information_schema.columns WHERE table_schema='analytics' AND table_name='report_exec_summary' AND column_name='id';
  SELECT data_type INTO t_title FROM information_schema.columns WHERE table_schema='analytics' AND table_name='report_exec_summary' AND column_name='title';
  SELECT data_type INTO t_result FROM information_schema.columns WHERE table_schema='analytics' AND table_name='report_exec_summary' AND column_name='result';
  SELECT data_type INTO t_signed FROM information_schema.columns WHERE table_schema='analytics' AND table_name='report_exec_summary' AND column_name='signed_out_at';

  IF t_id NOT IN ('text','character varying') THEN
    RAISE EXCEPTION 'Unexpected id type: %', t_id;
  END IF;
  IF t_title NOT IN ('text','character varying') THEN
    RAISE EXCEPTION 'Unexpected title type: %', t_title;
  END IF;
  IF t_result NOT IN ('text','character varying') THEN
    RAISE EXCEPTION 'Unexpected result type: %', t_result;
  END IF;
  IF t_signed NOT IN ('timestamp with time zone','timestamp without time zone') THEN
    RAISE EXCEPTION 'Unexpected signed_out_at type: %', t_signed;
  END IF;
END$$;

COMMIT;
