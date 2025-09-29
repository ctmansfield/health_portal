-- 060_labs_views_shared.sql
-- Provides catalog-backed shared labs views used by the UI and API.
-- - analytics.labs_metric_catalog: reference mapping for LOINC-coded labs with labels, groups, and sensitivity flags
-- - analytics.v_labs_all: per-person per-day lab series (median per day) with human-friendly labels
-- - analytics.v_labs_all_grouped: available lab metrics for each person with grouping metadata

CREATE SCHEMA IF NOT EXISTS analytics;

CREATE TABLE IF NOT EXISTS analytics.labs_metric_catalog (
  code_system   text    NOT NULL DEFAULT 'LOINC',
  code          text    NOT NULL,
  label         text    NOT NULL,
  label_key_norm text   GENERATED ALWAYS AS (lower(regexp_replace(label, '\\s+', ' ', 'g'))) STORED,
  group_name    text    NOT NULL DEFAULT 'Other',
  sensitive     boolean NOT NULL DEFAULT false,
  unit          text,
  enabled       boolean NOT NULL DEFAULT true,
  PRIMARY KEY (code_system, code)
);

-- Seed a useful subset; idempotent upsert
INSERT INTO analytics.labs_metric_catalog (code_system, code, label, group_name, sensitive, unit, enabled)
VALUES
  -- Liver Function Tests
  ('LOINC','1742-6','ALT','Liver Function Tests', false, 'U/L', true),
  ('LOINC','1920-8','AST','Liver Function Tests', false, 'U/L', true),
  ('LOINC','6768-6','ALP','Liver Function Tests', false, 'U/L', true),
  ('LOINC','2324-2','GGT','Liver Function Tests', false, 'U/L', true),
  ('LOINC','1975-2','Bilirubin Total','Liver Function Tests', false, 'mg/dL', true),
  ('LOINC','1968-7','Bilirubin Direct','Liver Function Tests', false, 'mg/dL', true),
  ('LOINC','1751-7','Albumin','Liver Function Tests', false, 'g/dL', true),
  -- Basic Metabolic
  ('LOINC','2345-7','Glucose','Metabolic Panel', false, 'mg/dL', true),
  ('LOINC','2160-0','Creatinine','Metabolic Panel', false, 'mg/dL', true),
  ('LOINC','17861-6','Calcium','Metabolic Panel', false, 'mg/dL', true),
  ('LOINC','2951-2','Sodium','Metabolic Panel', false, 'mmol/L', true),
  ('LOINC','2823-3','Potassium','Metabolic Panel', false, 'mmol/L', true),
  ('LOINC','2075-0','Chloride','Metabolic Panel', false, 'mmol/L', true),
  ('LOINC','2028-9','Carbon Dioxide','Metabolic Panel', false, 'mmol/L', true),
  -- CBC
  ('LOINC','6690-2','WBC','Complete Blood Count', false, '10^3/uL', true),
  ('LOINC','789-8','RBC','Complete Blood Count', false, '10^6/uL', true),
  ('LOINC','718-7','Hemoglobin','Complete Blood Count', false, 'g/dL', true),
  ('LOINC','20570-8','Hematocrit','Complete Blood Count', false, '%', true),
  ('LOINC','777-3','Platelet Count','Complete Blood Count', false, '10^3/uL', true),
  ('LOINC','787-2','MCV','Complete Blood Count', false, 'fL', true),
  ('LOINC','785-6','MCH','Complete Blood Count', false, 'pg', true),
  ('LOINC','786-4','MCHC','Complete Blood Count', false, 'g/dL', true),
  ('LOINC','788-0','RDW','Complete Blood Count', false, '%', true),
  ('LOINC','32623-1','MPV','Complete Blood Count', false, 'fL', true),
  -- Lipids
  ('LOINC','2093-3','Cholesterol Total','Lipids', false, 'mg/dL', true),
  ('LOINC','2085-9','HDL Cholesterol','Lipids', false, 'mg/dL', true),
  ('LOINC','2571-8','Triglycerides','Lipids', false, 'mg/dL', true),
  ('LOINC','18262-6','LDL Cholesterol (Direct)','Lipids', false, 'mg/dL', true),
  -- Thyroid/A1c
  ('LOINC','3016-3','TSH','Hormones', false, 'uIU/mL', true),
  ('LOINC','3024-7','Free Thyroxine (T4)','Hormones', false, 'ng/dL', true),
  ('LOINC','4548-4','Hemoglobin A1c','Metabolic Panel', false, '%', true),
  -- Others
  ('LOINC','2885-2','Protein Total','Metabolic Panel', false, 'g/dL', true),
  ('LOINC','3094-0','Urea Nitrogen (BUN)','Metabolic Panel', false, 'mg/dL', true),
  ('LOINC','2132-9','Vitamin B12','Miscellaneous', false, 'pg/mL', true),
  ('LOINC','2157-6','CPK Total','Miscellaneous', false, 'U/L', true),
  ('LOINC','20568-2','Prolactin','Hormones', false, 'ng/mL', true),
  ('LOINC','2857-1','PSA Total','Miscellaneous', true,  'ng/mL', true),
  ('LOINC','4537-7','Sed Rate (Westergren)','Miscellaneous', false, 'mm/h', true)
ON CONFLICT (code_system, code) DO UPDATE
SET label=EXCLUDED.label,
    group_name=EXCLUDED.group_name,
    sensitive=EXCLUDED.sensitive,
    unit=EXCLUDED.unit,
    enabled=EXCLUDED.enabled;

-- Drop old views to avoid CREATE OR REPLACE column-drop errors when shapes changed
DROP VIEW IF EXISTS analytics.v_labs_metadata_person CASCADE;
DROP VIEW IF EXISTS analytics.v_labs_all_grouped CASCADE;
DROP VIEW IF EXISTS analytics.v_labs_all CASCADE;

-- Per-person daily lab values with human labels from catalog
CREATE OR REPLACE VIEW analytics.v_labs_all AS
WITH src AS (
  SELECT
    e.person_id,
    (e.effective_time AT TIME ZONE 'UTC')::date AS day,
    c.label,
    c.label_key_norm,
    e.value_num
  FROM analytics.data_events e
  JOIN analytics.labs_metric_catalog c
    ON e.code_system ILIKE c.code_system
   AND e.code = c.code
  WHERE e.value_num IS NOT NULL
    AND c.enabled IS TRUE
)
SELECT
  person_id,
  label,
  label_key_norm,
  day,
  percentile_disc(0.5) WITHIN GROUP (ORDER BY value_num) AS value_num
FROM src
GROUP BY person_id, label, label_key_norm, day
ORDER BY person_id, label, day;

-- Available metrics for a person, with grouping and sensitivity metadata
CREATE OR REPLACE VIEW analytics.v_labs_all_grouped AS
SELECT DISTINCT
  e.person_id,
  c.label,
  c.label_key_norm,
  c.group_name,
  c.sensitive
FROM analytics.data_events e
JOIN analytics.labs_metric_catalog c
  ON e.code_system ILIKE c.code_system
 AND e.code = c.code
WHERE c.enabled IS TRUE;

