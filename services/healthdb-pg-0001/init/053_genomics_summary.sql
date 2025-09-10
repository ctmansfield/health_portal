-- 053_genomics_summary.sql
-- Materialized view summarizing genomics reports for the dashboard

CREATE MATERIALIZED VIEW IF NOT EXISTS analytics.mv_genomics_summary AS
WITH src AS (
  SELECT person_id, generated_at::date AS day, summary
  FROM analytics.genomics_reports
  WHERE generated_at IS NOT NULL
)
SELECT person_id, day,
       count(*) AS reports_count,
       jsonb_agg(summary) FILTER (WHERE summary IS NOT NULL) AS summaries
FROM src
GROUP BY person_id, day
ORDER BY person_id, day DESC;

CREATE INDEX IF NOT EXISTS idx_mv_genomics_summary_person_day ON analytics.mv_genomics_summary(person_id, day);
