-- 054_seed_demo.sql
-- Seed deterministic demo data for local development and integration tests.
-- Inserts sample events, genomics_reports, and ai_findings for person_id 'me'.

-- Events: 30 days of HR and SpO2
WITH days AS (
  SELECT generate_series::date AS day
  FROM generate_series(now()::date - interval '29 days', now()::date, interval '1 day')
)
INSERT INTO analytics.data_events (person_id, source, kind, code_system, code, display, effective_time, value_num, unit, meta)
SELECT
  'me'::text,
  'seed'::text,
  'Observation'::text,
  'LOINC'::text,
  CASE WHEN (d.generate_series::date % 2) = 0 THEN '8867-4' ELSE '59408-5' END,
  CASE WHEN (d.generate_series::date % 2) = 0 THEN 'Heart rate' ELSE 'SpO2' END,
  (d.generate_series + (interval '06:00'))::timestamptz,
  CASE WHEN (d.generate_series::date % 2) = 0 THEN 60 + ((extract(day from d.generate_series)::int % 5) * 2)::numeric ELSE (0.94 + ((extract(day from d.generate_series)::int % 6) * 0.01)) END,
  CASE WHEN (d.generate_series::date % 2) = 0 THEN '1/min' ELSE '%' END,
  jsonb_build_object('seeded', true)
FROM generate_series(now()::date - interval '29 days', now()::date, interval '1 day') d
ON CONFLICT ON CONSTRAINT uq_events_person_metric_time DO NOTHING;

-- Genomics reports: 10 demo reports
INSERT INTO analytics.genomics_reports (report_id, person_id, filename, path, generated_at, summary)
SELECT
  'demo-report-' || seq::text AS report_id,
  'me'::text,
  'demo-report-' || seq::text || '.pdf' AS filename,
  '/tmp/demo-report-' || seq::text || '.pdf' AS path,
  (now() - (seq || ' days')::interval)::timestamptz AS generated_at,
  jsonb_build_object('summary', 'demo report '||seq::text)
FROM generate_series(1,10) seq
ON CONFLICT (report_id) DO NOTHING;

-- AI findings: simple zscore-style findings for HR
INSERT INTO analytics.ai_findings (person_id, finding_time, metric, method, score, level, "window", context)
SELECT
  'me'::text,
  (now() - (i || ' days')::interval)::timestamptz AS finding_time,
  'hr'::text,
  'zscore'::text,
  ((i % 7) - 3)::numeric AS score,
  CASE WHEN abs((i % 7) - 3) >= 3 THEN 'alert' WHEN abs((i % 7) - 3) >= 2 THEN 'warn' ELSE 'info' END,
  jsonb_build_object('n', 21, 'metric', 'hr'),
  jsonb_build_object('seed', true)
FROM generate_series(1,14) i
ON CONFLICT (person_id, finding_time, metric) DO NOTHING;

-- Index for quick day-based lookups on genomics summary (if view materialized)
-- (No-op if view not present yet)
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_matviews WHERE matviewname = 'mv_genomics_summary') THEN
    EXECUTE 'CREATE INDEX IF NOT EXISTS idx_mv_genomics_summary_day ON analytics.mv_genomics_summary(day)';
  END IF;
END$$;
