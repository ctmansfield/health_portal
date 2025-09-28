-- 058_fhir_flat_ext.sql
-- Extended flat view for FHIR Observation including subject/person_id and text values.
-- Non-destructive: creates a new view fhir_raw.v_observation_flat_ext

CREATE OR REPLACE VIEW fhir_raw.v_observation_flat_ext AS
SELECT
  r.resource->>'id' AS id,
  COALESCE((r.resource->'meta'->>'lastUpdated')::timestamptz, r.imported_at) AS last_updated,
  (r.resource->>'status') AS status,
  -- subject reference is usually "Patient/{id}"; strip optional prefix
  NULLIF(REGEXP_REPLACE(COALESCE(r.resource #>> '{subject,reference}', ''), '^Patient\/', ''), '') AS person_id,
  -- effective time (DateTime or Period.start if present)
  COALESCE(
    NULLIF((r.resource->>'effectiveDateTime')::text, '')::timestamptz,
    NULLIF((r.resource #>> '{effectivePeriod,start}'), '')::timestamptz
  ) AS effective_time,
  lower((r.resource#>>'{code,coding,0,system}'))       AS code_system,
  (r.resource#>>'{code,coding,0,code}')                AS code,
  COALESCE((r.resource#>>'{code,coding,0,display}'), (r.resource->>'code')) AS display,
  (r.resource#>>'{valueQuantity,value}')::float        AS value_num,
  NULLIF((r.resource#>>'{valueQuantity,unit}'),'')     AS unit,
  -- Common places for non-numeric values
  NULLIF(
    COALESCE(
      r.resource #>> '{valueString}',
      r.resource #>> '{valueCodeableConcept,text}',
      r.resource #>> '{valueCodeableConcept,coding,0,display}'
    ), ''
  ) AS value_text,
  -- Interpretation if provided
  NULLIF(COALESCE(
      r.resource #>> '{interpretation,0,text}',
      r.resource #>> '{interpretation,0,coding,0,display}'
  ), '') AS interpretation,
  r.resource                                           AS resource
FROM fhir_raw.resources r
WHERE r.resource_type='Observation';

-- Simple counts helper
CREATE OR REPLACE VIEW fhir_raw.v_observation_counts_ext AS
SELECT code_system, code, count(*) AS n
FROM fhir_raw.v_observation_flat_ext
GROUP BY 1,2
ORDER BY n DESC;