CREATE OR REPLACE VIEW fhir_raw.v_observation_flat AS
SELECT
  r.resource->>'id' AS id,
  COALESCE((r.resource->'meta'->>'lastUpdated')::timestamptz, r.imported_at) AS last_updated,
  (r.resource->'effectiveDateTime')::text::timestamptz                        AS effective_time,
  lower((r.resource#>>'{code,coding,0,system}'))       AS code_system,
  (r.resource#>>'{code,coding,0,code}')                AS code,
  (r.resource#>>'{code,coding,0,display}')             AS display,
  (r.resource#>>'{valueQuantity,value}')::float        AS value_num,
  (r.resource#>>'{valueQuantity,unit}')                AS unit,
  r.resource                                          AS resource
FROM fhir_raw.resources r
WHERE r.resource_type='Observation';

CREATE OR REPLACE VIEW fhir_raw.v_observation_counts AS
SELECT code_system, code, count(*) AS n
FROM fhir_raw.v_observation_flat
GROUP BY 1,2
ORDER BY n DESC;
