-- 055_genomics_summary_indexes.sql
-- Additional indexes to support queries on the genomics summary materialized view

CREATE INDEX IF NOT EXISTS idx_mv_genomics_summary_day ON analytics.mv_genomics_summary(day);
CREATE INDEX IF NOT EXISTS idx_mv_genomics_summary_person ON analytics.mv_genomics_summary(person_id);
-- Consider GIN index on summaries for jsonb containment queries
CREATE INDEX IF NOT EXISTS idx_mv_genomics_summary_summaries_gin ON analytics.mv_genomics_summary USING GIN (summaries);
