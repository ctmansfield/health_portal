-- Unique ON (resource_type, id) to enforce one copy per resource
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_indexes
    WHERE schemaname='fhir_raw' AND indexname='ux_fhir_resources_type_id'
  ) THEN
    EXECUTE $DDL$
      CREATE UNIQUE INDEX ux_fhir_resources_type_id
      ON fhir_raw.resources(resource_type, (resource->>'id'));
    $DDL$;
  END IF;
END$$;
