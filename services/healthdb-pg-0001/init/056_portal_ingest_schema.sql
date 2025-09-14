
-- 056_portal_ingest_schema.sql
-- Creates an ingestion schema for parsed portal text/CSV lab results.
-- Safe to run multiple times.

CREATE SCHEMA IF NOT EXISTS ingest_portal;

-- raw import runs (minimal run metadata)
CREATE TABLE IF NOT EXISTS ingest_portal.import_run (
  run_id UUID PRIMARY KEY,
  source_file TEXT NOT NULL,
  started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  finished_at TIMESTAMPTZ,
  person_id TEXT NOT NULL,
  importer_version TEXT,
  notes TEXT
);

-- staging table for parsed lab rows (one row per observation)
CREATE TABLE IF NOT EXISTS ingest_portal.stg_portal_labs (
  run_id UUID NOT NULL,
  person_id TEXT NOT NULL,
  provider TEXT,
  test_name TEXT NOT NULL,
  value_num DOUBLE PRECISION,
  unit TEXT,
  flag TEXT,
  reference_text TEXT,
  effective_time TIMESTAMPTZ NOT NULL,
  code_system TEXT,       -- 'LOINC' if mapped, else 'LOCAL'
  code TEXT,              -- LOINC code or normalized local code
  src_line TEXT,          -- raw text/line for traceability
  src_page INT,
  src_order INT,          -- order within a page/section
  src_hash TEXT NOT NULL, -- hash of the raw row for dedupe across runs
  imported_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  meta JSONB DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_stg_portal_labs_hash ON ingest_portal.stg_portal_labs(src_hash);
CREATE INDEX IF NOT EXISTS idx_stg_portal_labs_eff ON ingest_portal.stg_portal_labs(effective_time);
CREATE INDEX IF NOT EXISTS idx_stg_portal_labs_code ON ingest_portal.stg_portal_labs(code);

-- rejected/invalid rows (parsable but not importable, e.g., 'SEE NOTE', text values)
CREATE TABLE IF NOT EXISTS ingest_portal.rejections (
  run_id UUID NOT NULL,
  reason TEXT NOT NULL,
  provider TEXT,
  raw_text TEXT,
  parsed JSONB,
  effective_time TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- duplicate rows (within-run or across previous runs)
CREATE TABLE IF NOT EXISTS ingest_portal.dup_log (
  run_id UUID NOT NULL,
  src_hash TEXT NOT NULL,
  reason TEXT NOT NULL,
  details JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
