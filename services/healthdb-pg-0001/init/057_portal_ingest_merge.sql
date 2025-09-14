
-- 057_portal_ingest_merge.sql
-- Moves staged rows from ingest_portal.stg_portal_labs into analytics.data_events
-- while avoiding duplicates already present.

-- Expected analytics.data_events columns (verify in your DB):
-- person_id TEXT, code_system TEXT, code TEXT, value_num DOUBLE PRECISION,
-- unit TEXT, effective_time TIMESTAMPTZ, meta JSONB

-- Parameterized by :run_id (psql -v), see install/verify scripts or the Python tool.

WITH ins AS (
  SELECT
    s.person_id, s.code_system, s.code, s.value_num, s.unit, s.effective_time,
    COALESCE(s.meta, '{}'::jsonb) ||
      jsonb_build_object(
        'source', 'portal_pdf',
        'provider', s.provider,
        'src_hash', s.src_hash,
        'src_line', s.src_line,
        'src_page', s.src_page,
        'src_order', s.src_order,
        'imported_at', to_char(s.imported_at, 'YYYY-MM-DD"T"HH24:MI:SSOF'),
        'run_id', s.run_id::text
      ) AS meta
  FROM ingest_portal.stg_portal_labs s
  WHERE s.run_id = :'run_id'
)
INSERT INTO analytics.data_events (person_id, code_system, code, value_num, unit, effective_time, meta)
SELECT i.person_id, i.code_system, i.code, i.value_num, i.unit, i.effective_time, i.meta
FROM ins i
LEFT JOIN analytics.data_events a
  ON a.person_id = i.person_id
 AND a.code_system = i.code_system
 AND a.code = i.code
 AND a.effective_time = i.effective_time
 AND ( (a.value_num IS NOT DISTINCT FROM i.value_num) AND COALESCE(a.unit,'') = COALESCE(i.unit,'') )
WHERE a.person_id IS NULL;
