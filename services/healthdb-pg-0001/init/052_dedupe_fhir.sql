-- Remove duplicate FHIR resources keeping the newest lastUpdated/imported_at
WITH ranked AS (
  SELECT ctid, resource_type,
         resource->>'id' AS rid,
         COALESCE((resource->'meta'->>'lastUpdated')::timestamptz, imported_at) AS ts,
         ROW_NUMBER() OVER (
           PARTITION BY resource_type, resource->>'id'
           ORDER BY COALESCE((resource->'meta'->>'lastUpdated')::timestamptz, imported_at) DESC
         ) AS rn
  FROM fhir_raw.resources
  WHERE resource ? 'id'
)
DELETE FROM fhir_raw.resources r
USING ranked d
WHERE r.ctid = d.ctid
  AND d.rn > 1;
