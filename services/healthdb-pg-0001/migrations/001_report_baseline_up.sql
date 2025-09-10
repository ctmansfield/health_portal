-- 001_report_baseline_up.sql
-- Migration: create baseline report, variant, biomarker tables + indexes + report_exec_summary view
-- Safe for Postgres v14+. Idempotent where supported. Wrapped in a single transaction.

BEGIN;
-- Timeouts to avoid long locks in shared environments
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '2min';

-- Ensure analytics schema exists (no-op if already present)
CREATE SCHEMA IF NOT EXISTS analytics;

-- Provide uuid generator (pgcrypto provides gen_random_uuid())
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Reports table: canonical payload + normalized columns
CREATE TABLE IF NOT EXISTS analytics.report (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  report_id text UNIQUE,
  person_id text,
  title text,
  result text,
  payload jsonb NOT NULL DEFAULT '{}'::jsonb,
  signed_out_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now()
);
COMMENT ON TABLE analytics.report IS 'Canonical clinician reports (payload) with optional normalized columns (title,result,signed_out_at)';

-- Variants (normalized) linked to report.id
CREATE TABLE IF NOT EXISTS analytics.variant (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  report_id uuid NOT NULL,
  gene_symbol text,
  hgvs text,
  consequence text,
  allele_freq double precision,
  raw jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT fk_variant_report FOREIGN KEY (report_id) REFERENCES analytics.report(id) ON DELETE CASCADE
);
COMMENT ON TABLE analytics.variant IS 'Normalized variant rows linked to canonical report payload';

-- Biomarkers (normalized) linked to report.id
CREATE TABLE IF NOT EXISTS analytics.biomarker (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  report_id uuid NOT NULL,
  name text,
  value_text text,
  value_num double precision,
  unit text,
  raw jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT fk_biomarker_report FOREIGN KEY (report_id) REFERENCES analytics.report(id) ON DELETE CASCADE
);
COMMENT ON TABLE analytics.biomarker IS 'Normalized biomarker rows linked to canonical report payload';

-- Indexes
-- GIN index on report.payload for fast JSONB queries (e.g., findings.variants.geneSymbol)
CREATE INDEX IF NOT EXISTS idx_report_payload_gin ON analytics.report USING gin (payload jsonb_path_ops);
-- B-tree on signed_out_at for time-range queries
CREATE INDEX IF NOT EXISTS idx_report_signed_out_at ON analytics.report (signed_out_at);
-- B-tree on variant.gene_symbol for gene-based filters
CREATE INDEX IF NOT EXISTS idx_variant_gene_symbol ON analytics.variant (gene_symbol);
-- Optional: index on biomarker.name for common lookups
CREATE INDEX IF NOT EXISTS idx_biomarker_name ON analytics.biomarker (name);

-- Create or replace view report_exec_summary projecting normalized columns when available
CREATE OR REPLACE VIEW analytics.report_exec_summary AS
SELECT
  r.id::text AS id,
  COALESCE(r.title, r.payload->> 'title') AS title,
  -- result banner: prefer normalized column, then common payload locations
  COALESCE(
    r.result,
    r.payload->> 'result',
    r.payload->> 'outcome',
    (r.payload-> 'summary') ->> 'banner',
    (r.payload-> 'summary') ->> 'result'
  ) AS result,
  r.signed_out_at
FROM analytics.report r;

COMMENT ON VIEW analytics.report_exec_summary IS 'Execution summary for reports (id,title,result,signed_out_at) - projects normalized columns then JSON payload';

COMMIT;

--
-- Tiny smoke-seed example (commented out). Use for manual verification only.
--
-- BEGIN;
-- INSERT INTO analytics.report(report_id, person_id, title, result, payload, signed_out_at)
-- VALUES (
--   'rpt-0001', 'person-123', 'Test Report Title', 'POSITIVE',
--   '{"title":"Test Report Title","result":"POSITIVE","summary":{"banner":"POSITIVE"}}'::jsonb,
--   now());
--
-- -- Link a variant and biomarker
-- INSERT INTO analytics.variant(report_id, gene_symbol, hgvs, consequence, raw)
-- VALUES ((SELECT id FROM analytics.report WHERE report_id='rpt-0001'), 'TP53', 'NM_000546.5:c.215C>G', 'missense_variant', '{}');
--
-- INSERT INTO analytics.biomarker(report_id, name, value_text, value_num, unit)
-- VALUES ((SELECT id FROM analytics.report WHERE report_id='rpt-0001'), 'Hemoglobin', 'low', 11.2, 'g/dL');
--
-- COMMIT;
