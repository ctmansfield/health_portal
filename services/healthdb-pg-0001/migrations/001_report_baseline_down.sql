-- 001_report_baseline_down.sql
-- Rollback migration: drops view, indexes, and tables created by 001_report_baseline_up.sql
-- Wrapped in a single transaction. Idempotent where supported.

BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '2min';

-- Drop view if exists
DROP VIEW IF EXISTS analytics.report_exec_summary CASCADE;

-- Drop indexes (IF EXISTS) - some will be implicitly dropped with tables, but explicit drops are safe
DROP INDEX IF EXISTS analytics.idx_report_payload_gin;
DROP INDEX IF EXISTS analytics.idx_report_signed_out_at;
DROP INDEX IF EXISTS analytics.idx_variant_gene_symbol;
DROP INDEX IF EXISTS analytics.idx_biomarker_name;

-- Drop normalized tables in reverse dependency order
DROP TABLE IF EXISTS analytics.variant CASCADE;
DROP TABLE IF EXISTS analytics.biomarker CASCADE;
DROP TABLE IF EXISTS analytics.report CASCADE;

-- Note: we do not drop the analytics schema nor the pgcrypto extension here to avoid impacting other objects.

COMMIT;
