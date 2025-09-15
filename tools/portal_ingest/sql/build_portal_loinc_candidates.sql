\set ON_ERROR_STOP on
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- expects: -v RUN_ID=<uuid>  [-v SIM=<0.55..1.0>]  (default SIM=0.60)
\if :{?SIM}
\else
\set SIM 0.60
\endif

-- 1) Local codes from this run
CREATE TEMP TABLE _local AS
SELECT DISTINCT
  s.run_id,
  UPPER(s.test_name)           AS local_code,
  s.test_name                  AS local_display,
  NULLIF(s.unit,'')            AS unit
FROM ingest_portal.stg_portal_labs s
WHERE s.run_id = :'RUN_ID'::uuid;

-- 2) Build a display corpus for LOINC (prefer fhir_raw, fallback to analytics)
DO $$
BEGIN
  IF EXISTS (
      SELECT 1 FROM information_schema.tables
      WHERE table_schema='fhir_raw' AND table_name='v_observation_flat'
  ) THEN
    EXECUTE 'CREATE TEMP TABLE loinc_disp AS
      SELECT DISTINCT code AS loinc_code, display AS loinc_display
      FROM fhir_raw.v_observation_flat
      WHERE code_system ILIKE ''%loinc%''
        AND code ~ ''^[0-9]+-[0-9]+$''
        AND display IS NOT NULL';
  ELSE
    EXECUTE 'CREATE TEMP TABLE loinc_disp AS
      SELECT DISTINCT code AS loinc_code,
             COALESCE(code_display, code) AS loinc_display
      FROM analytics.data_events
      WHERE code_system=''LOINC''
        AND code ~ ''^[0-9]+-[0-9]+$''';
  END IF;
END$$;

-- 3) Candidates via trigram similarity
CREATE TEMP TABLE _cand AS
SELECT
  l.run_id,
  l.local_code,
  l.local_display,
  l.unit,
  d.loinc_code,
  d.loinc_display,
  GREATEST(
    similarity(upper(l.local_display), upper(d.loinc_display)),
    similarity(upper(l.local_code),    upper(d.loinc_display))
  ) AS sim
FROM _local l
JOIN loinc_disp d
  ON (upper(d.loinc_display) % upper(l.local_display)
      OR upper(d.loinc_display) % upper(l.local_code));

-- 4) Best suggestion per local_code, above SIM threshold, and not already mapped
CREATE TEMP TABLE _best AS
SELECT DISTINCT ON (c.local_code) c.*
FROM _cand c
LEFT JOIN ingest_portal.code_map_local_to_loinc m
  ON m.source='portal' AND m.local_code = c.local_code
WHERE m.local_code IS NULL
  AND c.sim >= :'SIM'
ORDER BY c.local_code, c.sim DESC;

-- 5) Final table to curate candidates
CREATE TABLE IF NOT EXISTS ingest_portal.portal_loinc_candidates (
  run_id        uuid,
  local_code    text,
  local_display text,
  unit          text,
  loinc_code    text,
  loinc_display text,
  sim           numeric,
  decided       boolean DEFAULT false,
  accepted      boolean,
  decided_at    timestamptz,
  PRIMARY KEY (run_id, local_code)
);

-- 6) Idempotent upsert unless already decided
INSERT INTO ingest_portal.portal_loinc_candidates
(run_id,local_code,local_display,unit,loinc_code,loinc_display,sim)
SELECT run_id,local_code,local_display,unit,loinc_code,loinc_display,sim
FROM _best
ON CONFLICT (run_id, local_code) DO UPDATE
SET loinc_code    = EXCLUDED.loinc_code,
    loinc_display = EXCLUDED.loinc_display,
    sim           = EXCLUDED.sim
WHERE ingest_portal.portal_loinc_candidates.decided IS NOT TRUE;
