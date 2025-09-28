-- 059_lab_reimport.sql
-- Reimport pipeline to load all lab data anew into a parallel table for comparison.
-- Steps:
-- 1) Create a new comparison table analytics.data_events_new with same structure as analytics.data_events
-- 2) Provide staging table analytics.lab_ingest_raw_mdjson for mdjson/FHIR-normalized rows
-- 3) Transform from mdjson/FHIR into data_events_new
-- 4) Provide validation helpers to diff old vs new

CREATE SCHEMA IF NOT EXISTS analytics;
CREATE SCHEMA IF NOT EXISTS ingest_portal;

-- 1) New target table mirroring analytics.data_events
CREATE TABLE IF NOT EXISTS analytics.data_events_new (
  id bigserial PRIMARY KEY,
  person_id       text NOT NULL,
  source          text NOT NULL,
  kind            text NOT NULL,
  code_system     text,
  code            text,
  display         text,
  effective_time  timestamptz,
  effective_start timestamptz,
  effective_end   timestamptz,
  value_num       double precision,
  value_text      text,
  unit            text,
  device_id       text,
  status          text,
  raw             jsonb NOT NULL,
  meta            jsonb
);
CREATE INDEX IF NOT EXISTS de_new_person_time   ON analytics.data_events_new (person_id, effective_time);
CREATE INDEX IF NOT EXISTS de_new_person_period ON analytics.data_events_new (person_id, effective_start, effective_end);
CREATE INDEX IF NOT EXISTS de_new_code          ON analytics.data_events_new (code_system, code);
CREATE INDEX IF NOT EXISTS de_new_raw_gin       ON analytics.data_events_new USING gin (raw jsonb_path_ops);

-- 2) Staging table for normalized MDJSON lines (one JSON object per row) or FHIR Observation JSON
-- Expect each row to include at minimum: person_id, effective_time (timestamptz),
-- code_system ('LOINC' or 'LOCAL'), code, display, value_num or value_text, unit, status, and a raw payload.
CREATE TABLE IF NOT EXISTS analytics.lab_ingest_raw_mdjson (
  id bigserial PRIMARY KEY,
  person_id     text,
  payload       jsonb NOT NULL,
  ingested_at   timestamptz NOT NULL DEFAULT now(),
  source        text,
  note          text
);
CREATE INDEX IF NOT EXISTS idx_lab_ingest_raw_mdjson_person ON analytics.lab_ingest_raw_mdjson(person_id);
CREATE INDEX IF NOT EXISTS idx_lab_ingest_raw_mdjson_gin     ON analytics.lab_ingest_raw_mdjson USING gin (payload jsonb_path_ops);

-- 3) Transform: From MDJSON/FHIR payloads into analytics.data_events_new
-- Prefer FHIR Observation if payload contains resourceType='Observation'; else assume MDJSON canonical schema:
--   {
--     "person_id": "...",
--     "effective_time": "2025-09-01T00:00:00Z",
--     "code_system": "LOINC",
--     "code": "1742-6",
--     "display": "ALT",
--     "value_num": 23.0,
--     "value_text": null,
--     "unit": "U/L",
--     "status": "final",
--     "source": "portal",
--     "raw": { ... original ... },
--     "meta": { ... }
--   }

CREATE OR REPLACE FUNCTION analytics.load_data_events_new_from_mdjson()
RETURNS bigint LANGUAGE plpgsql AS $$
DECLARE
  n_inserted bigint := 0;
BEGIN
  -- Insert MDJSON rows
  INSERT INTO analytics.data_events_new (
    person_id, source, kind, code_system, code, display, effective_time,
    value_num, value_text, unit, status, raw, meta
  )
  SELECT
    COALESCE(payload->>'person_id', person_id),
    COALESCE(payload->>'source', 'mdjson') AS source,
    COALESCE(payload->>'kind', 'observation') AS kind,
    NULLIF(payload->>'code_system','') AS code_system,
    NULLIF(payload->>'code','') AS code,
    NULLIF(payload->>'display','') AS display,
    NULLIF(payload->>'effective_time','')::timestamptz AS effective_time,
    (payload->>'value_num')::double precision AS value_num,
    NULLIF(payload->>'value_text','') AS value_text,
    NULLIF(payload->>'unit','') AS unit,
    NULLIF(payload->>'status','') AS status,
    COALESCE(payload->'raw', payload) AS raw,
    payload->'meta'
  FROM analytics.lab_ingest_raw_mdjson m
  WHERE (payload->>'resourceType') IS NULL -- not FHIR, MDJSON only
    AND (payload ? 'effective_time');

  GET DIAGNOSTICS n_inserted = ROW_COUNT;

  -- Insert FHIR Observation rows present in MDJSON staging (if any)
  INSERT INTO analytics.data_events_new (
    person_id, source, kind, code_system, code, display, effective_time,
    value_num, value_text, unit, status, raw, meta
  )
  SELECT
    NULLIF(REGEXP_REPLACE(COALESCE(payload #>> '{subject,reference}', ''), '^Patient\/',''),'') AS person_id,
    'fhir' AS source,
    'observation' AS kind,
    lower(payload #>> '{code,coding,0,system}') AS code_system,
    payload #>> '{code,coding,0,code}' AS code,
    COALESCE(payload #>> '{code,coding,0,display}', payload->>'code') AS display,
    COALESCE(
      NULLIF(payload->>'effectiveDateTime','')::timestamptz,
      NULLIF(payload #>> '{effectivePeriod,start}','')::timestamptz
    ) AS effective_time,
    (payload #>> '{valueQuantity,value}')::double precision AS value_num,
    COALESCE(payload->>'valueString', payload #>> '{valueCodeableConcept,text}', payload #>> '{valueCodeableConcept,coding,0,display}') AS value_text,
    NULLIF(payload #>> '{valueQuantity,unit}','') AS unit,
    NULLIF(payload->>'status','') AS status,
    payload AS raw,
    NULL::jsonb AS meta
  FROM analytics.lab_ingest_raw_mdjson m
  WHERE payload->>'resourceType' = 'Observation'
    AND (
         payload ? 'effectiveDateTime' OR (payload ? 'effectivePeriod' AND payload #>> '{effectivePeriod,start}' IS NOT NULL)
    );

  GET DIAGNOSTICS n_inserted = n_inserted + ROW_COUNT;

  RETURN n_inserted;
END$$;

-- 4) Validation helpers: compare old vs new by person/code/time/value/unit
CREATE OR REPLACE VIEW analytics.v_data_events_diff AS
WITH old_norm AS (
  SELECT person_id, code_system, code, unit,
         effective_time,
         COALESCE(value_num, NULL) AS value_num
  FROM analytics.data_events
), new_norm AS (
  SELECT person_id, code_system, code, unit,
         effective_time,
         COALESCE(value_num, NULL) AS value_num
  FROM analytics.data_events_new
)
SELECT
  COALESCE(o.person_id, n.person_id) AS person_id,
  COALESCE(o.code_system, n.code_system) AS code_system,
  COALESCE(o.code, n.code) AS code,
  COALESCE(o.unit, n.unit) AS unit,
  o.effective_time AS old_time,
  n.effective_time AS new_time,
  o.value_num AS old_value,
  n.value_num AS new_value,
  CASE WHEN o.person_id IS NULL THEN 'added'
       WHEN n.person_id IS NULL THEN 'removed'
       WHEN o.value_num IS DISTINCT FROM n.value_num OR o.unit IS DISTINCT FROM n.unit THEN 'changed'
       ELSE 'same'
  END AS diff
FROM old_norm o
FULL OUTER JOIN new_norm n
  ON o.person_id = n.person_id
 AND o.code_system = n.code_system
 AND o.code = n.code
 AND o.effective_time = n.effective_time;

-- Optional: quick summary counts
CREATE OR REPLACE VIEW analytics.v_data_events_diff_summary AS
SELECT diff, count(*) AS n
FROM analytics.v_data_events_diff
GROUP BY diff
ORDER BY n DESC;