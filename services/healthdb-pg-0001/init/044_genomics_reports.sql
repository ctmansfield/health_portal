-- 044_genomics_reports.sql
-- Table to index genomics risk reports for dashboard & API

CREATE TABLE IF NOT EXISTS analytics.genomics_reports (
  id BIGSERIAL PRIMARY KEY,
  report_id text NOT NULL,
  person_id text,
  filename text NOT NULL,
  path text NOT NULL,
  generated_at timestamptz,
  summary jsonb DEFAULT '{}',
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_genomics_reports_person_generated ON analytics.genomics_reports(person_id, generated_at);
CREATE UNIQUE INDEX IF NOT EXISTS uq_genomics_reports_report_id ON analytics.genomics_reports(report_id);
