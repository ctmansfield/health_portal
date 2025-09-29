-- 061_catalog_add_vitals_off.sql
-- Add common vitals LOINC codes to labs_metric_catalog but keep them disabled (enabled=false)
-- This removes them from the "unmapped" query while keeping them out of v_labs_all and metadata.

INSERT INTO analytics.labs_metric_catalog (code_system, code, label, group_name, sensitive, unit, enabled)
VALUES
  ('LOINC','8867-4','Heart Rate','Vitals', false, 'bpm', false),
  ('LOINC','59408-5','Oxygen Saturation','Vitals', false, '%',   false),
  ('LOINC','29463-7','Body weight','Vitals', false, 'kg',  false)
ON CONFLICT (code_system, code) DO UPDATE
SET label=EXCLUDED.label,
    group_name=EXCLUDED.group_name,
    sensitive=EXCLUDED.sensitive,
    unit=EXCLUDED.unit,
    enabled=EXCLUDED.enabled;