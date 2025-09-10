-- Unique key over resource_type + JSON id to prevent re-import dupes
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_indexes
    WHERE schemaname='fhir_raw' AND indexname='ux_fhir_resource_type_id'
  ) THEN
    EXECUTE $DDL$
      CREATE UNIQUE INDEX ux_fhir_resource_type_id
        ON fhir_raw.resources (resource_type, ((resource->>'id')));
    $DDL$;
  END IF;
END$$;

-- Quick lens to see exact duplicates by (type,id)
CREATE OR REPLACE VIEW fhir_raw.v_resource_dupes AS
SELECT resource_type,
       resource->>'id' AS id,
       COUNT(*) AS n,
       MIN(imported_at) AS first_seen,
       MAX(imported_at) AS last_seen
FROM fhir_raw.resources
GROUP BY 1,2
HAVING COUNT(*) > 1
ORDER BY n DESC, last_seen DESC;
