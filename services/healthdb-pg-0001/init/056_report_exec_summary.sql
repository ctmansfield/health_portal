-- 056_report_exec_summary.sql
-- Add view expected by App & Dashboard: analytics.report_exec_summary
-- Columns required by the contract: id, title, result, signed_out_at

-- Ensure idempotent creation (drop first so re-applying is safe)
DROP VIEW IF EXISTS analytics.report_exec_summary CASCADE;

CREATE OR REPLACE VIEW analytics.report_exec_summary AS
SELECT
  report_id::text AS id,
  filename::text AS title,
  (
    -- prefer an explicit 'result' key in the JSON summary when present
    CASE
      WHEN summary ? 'result' THEN summary->> 'result'
      WHEN summary ? 'outcome' THEN summary->> 'outcome'
      ELSE NULL
    END
  )::text AS result,
  generated_at AS signed_out_at
FROM analytics.genomics_reports;

-- Add a simple comment for discoverability
COMMENT ON VIEW analytics.report_exec_summary IS 'Execution summary for reports (id,title,result,signed_out_at) - generated from analytics.genomics_reports';
