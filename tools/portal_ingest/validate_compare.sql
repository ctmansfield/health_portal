-- tools/portal_ingest/validate_compare.sql
-- Compare analytics.data_events (old) vs analytics.data_events_new (new)
-- Provides a quick diff and some normalization checks.

\echo 'Summary counts (old vs new)'
SELECT 'old' src, count(*) FROM analytics.data_events
UNION ALL
SELECT 'new' src, count(*) FROM analytics.data_events_new;

\echo '\nDiff breakdown (added/removed/changed/same)'
SELECT * FROM analytics.v_data_events_diff_summary;

\echo '\nExamples of changed rows (limit 50)'
SELECT * FROM analytics.v_data_events_diff WHERE diff='changed' LIMIT 50;

\echo '\nExamples of new rows (limit 50)'
SELECT * FROM analytics.v_data_events_diff WHERE diff='added' LIMIT 50;

\echo '\nExamples of removed rows (limit 50)'
SELECT * FROM analytics.v_data_events_diff WHERE diff='removed' LIMIT 50;

\echo '\nTop codes (new)'
SELECT code_system, code, unit, count(*) AS n
FROM analytics.data_events_new
GROUP BY 1,2,3
ORDER BY n DESC
LIMIT 50;
