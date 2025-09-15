CREATE SCHEMA IF NOT EXISTS ingest_portal;

CREATE TABLE IF NOT EXISTS ingest_portal.code_map_local_to_loinc (
  source         text    NOT NULL DEFAULT 'portal',
  local_code     text    NOT NULL,   -- UPPER(test_name)
  local_display  text,
  loinc_code     text    NOT NULL,
  loinc_display  text,
  src_unit       text,
  tgt_unit       text,
  comment        text,
  PRIMARY KEY (source, local_code)
);

-- Helper for idempotent upsert
WITH x(local_code,local_display,loinc_code,loinc_display,src_unit,tgt_unit,comment) AS (
  VALUES
  -- ===== Core chem / liver =====
  ('ALT','ALT','1742-6','Alanine aminotransferase [Enzymatic activity/volume] in Serum or Plasma','U/L','U/L',''),
  ('AST','AST','1920-8','Aspartate aminotransferase [Enzymatic activity/volume] in Serum or Plasma','U/L','U/L',''),
  ('ALKALINE PHOSPHATASE','ALKALINE PHOSPHATASE','6768-6','Alkaline phosphatase [Enzymatic activity/volume] in Serum or Plasma','U/L','U/L',''),
  ('GGT','GGT','2324-2','Gamma glutamyl transferase [Enzymatic activity/volume] in Serum or Plasma','U/L','U/L',''),
  ('BILIRUBIN, TOTAL','BILIRUBIN, TOTAL','1975-2','Bilirubin.total [Mass/volume] in Serum or Plasma','mg/dL','mg/dL',''),
  ('BILIRUBIN, DIRECT','BILIRUBIN, DIRECT','1968-7','Bilirubin.direct [Mass/volume] in Serum or Plasma','mg/dL','mg/dL',''),
  ('ALBUMIN','ALBUMIN','1751-7','Albumin [Mass/volume] in Serum or Plasma','g/dL','g/dL',''),
  ('GLUCOSE','GLUCOSE','2345-7','Glucose [Mass/volume] in Serum or Plasma','mg/dL','mg/dL',''),
  ('CREATININE','CREATININE','2160-0','Creatinine [Mass/volume] in Serum or Plasma','mg/dL','mg/dL',''),
  ('CALCIUM','CALCIUM','17861-6','Calcium [Mass/volume] in Serum or Plasma','mg/dL','mg/dL',''),
  ('SODIUM','SODIUM','2951-2','Sodium [Moles/volume] in Serum or Plasma','mmol/L','mmol/L',''),
  ('POTASSIUM','POTASSIUM','2823-3','Potassium [Moles/volume] in Serum or Plasma','mmol/L','mmol/L',''),
  ('CHLORIDE','CHLORIDE','2075-0','Chloride [Moles/volume] in Serum or Plasma','mmol/L','mmol/L',''),
  ('CO2','CO2','2028-9','Carbon dioxide, total [Moles/volume] in Serum or Plasma','mmol/L','mmol/L',''),
  ('CARBON DIOXIDE','CARBON DIOXIDE','2028-9','Carbon dioxide, total [Moles/volume] in Serum or Plasma','mmol/L','mmol/L',''),

  -- ===== CBC =====
  ('WBC','WBC','6690-2','Leukocytes [#/volume] in Blood by Automated count','Thousand/uL','10^3/uL','units may differ; verify scale'),
  ('RBC','RBC','789-8','Erythrocytes [#/volume] in Blood by Automated count','Million/uL','10^6/uL','units may differ; verify scale'),
  ('HEMOGLOBIN','HEMOGLOBIN','718-7','Hemoglobin [Mass/volume] in Blood','g/dL','g/dL',''),
  ('HEMATOCRIT','HEMATOCRIT','20570-8','Hematocrit [Volume Fraction] of Blood by Automated count','%','%','confirm vs 4544-3 in your data'),
  ('PLATELET COUNT','PLATELET COUNT','777-3','Platelets [#/volume] in Blood by Automated count','Thousand/uL','10^3/uL','units may differ; verify scale'),
  ('MCV','MCV','787-2','MCV [Entitic volume] by Automated count','fL','fL',''),
  ('MCH','MCH','785-6','MCH [Entitic mass] by Automated count','pg','pg',''),
  ('MCHC','MCHC','786-4','MCHC [Mass/volume] by Automated count','g/dL','g/dL',''),
  ('RDW','RDW','788-0','Erythrocyte distribution width [Ratio] by Automated count','%','%',''),
  ('RDW-CV','RDW-CV','788-0','Erythrocyte distribution width [Ratio] by Automated count','%','%',''),
  ('MPV','MPV','32623-1','Platelet mean volume [Entitic volume] in Blood by Automated count','fL','fL',''),

  -- ===== Lipids =====
  ('CHOLESTEROL, TOTAL','CHOLESTEROL, TOTAL','2093-3','Cholesterol [Mass/volume] in Serum or Plasma','mg/dL','mg/dL',''),
  ('CHOLESTEROL','CHOLESTEROL','2093-3','Cholesterol [Mass/volume] in Serum or Plasma','mg/dL','mg/dL',''),
  ('HDL CHOLESTEROL','HDL CHOLESTEROL','2085-9','Cholesterol in HDL [Mass/volume] in Serum or Plasma','mg/dL','mg/dL',''),
  ('TRIGLYCERIDES','TRIGLYCERIDES','2571-8','Triglyceride [Mass/volume] in Serum or Plasma','mg/dL','mg/dL',''),
  ('TRIGLYCERIDE','TRIGLYCERIDE','2571-8','Triglyceride [Mass/volume] in Serum or Plasma','mg/dL','mg/dL',''),
  ('DIRECT LDL CHOLESTEROL','DIRECT LDL CHOLESTEROL','18262-6','Cholesterol in LDL [Mass/volume] in Serum or Plasma by Direct assay','mg/dL','mg/dL',''),

  -- ===== Endocrine / thyroid / A1c =====
  ('TSH','TSH','3016-3','Thyrotropin [Units/volume] in Serum or Plasma','uIU/mL','uIU/mL',''),
  ('FREE THYROXINE (T4)','FREE THYROXINE (T4)','3024-7','Thyroxine (T4) free [Mass/volume] in Serum or Plasma','ng/dL','ng/dL',''),
  ('T4 (THYROXINE), TOTAL','T4 (THYROXINE), TOTAL','3026-2','Thyroxine (T4) [Mass/volume] in Serum or Plasma','ug/dL','ug/dL',''),
  ('T3, TOTAL','T3, TOTAL','3053-6','Triiodothyronine (T3) [Mass/volume] in Serum or Plasma','ng/dL','ng/dL',''),
  ('T3 UPTAKE','T3 UPTAKE','3050-2','Triiodothyronine (T3) uptake in Serum or Plasma',NULL,NULL,''),
  ('HEMOGLOBIN A1C','HEMOGLOBIN A1C','4548-4','Hemoglobin A1c/Hemoglobin.total in Blood','%','%',''),

  -- ===== Proteins & nitrogen =====
  ('PROTEIN, TOTAL','PROTEIN, TOTAL','2885-2','Protein [Mass/volume] in Serum or Plasma','g/dL','g/dL',''),
  ('PROTEIN,TOTAL','PROTEIN,TOTAL','2885-2','Protein [Mass/volume] in Serum or Plasma','g/dL','g/dL',''),
  ('UREA NITROGEN','UREA NITROGEN','3094-0','Urea nitrogen [Mass/volume] in Serum or Plasma','mg/dL','mg/dL',''),

  -- ===== Others in your run, clearly mappable =====
  ('VITAMIN B12','VITAMIN B12','2132-9','Vitamin B12 [Mass/volume] in Serum or Plasma','pg/mL','pg/mL',''),
  ('CPK, TOTAL','CPK, TOTAL','2157-6','Creatine kinase [Enzymatic activity/volume] in Serum or Plasma','U/L','U/L',''),
  ('PROLACTIN','PROLACTIN','20568-2','Prolactin [Mass/volume] in Serum or Plasma','ng/mL','ng/mL',''),
  ('PSA, TOTAL','PSA, TOTAL','2857-1','Prostate specific Ag [Mass/volume] in Serum or Plasma','ng/mL','ng/mL',''),
  ('PROSTATE SPECIFIC ANTIGEN','PROSTATE SPECIFIC ANTIGEN','2857-1','Prostate specific Ag [Mass/volume] in Serum or Plasma','ng/mL','ng/mL',''),
  ('PROSTATE SPECIFIC AG','PROSTATE SPECIFIC AG','2857-1','Prostate specific Ag [Mass/volume] in Serum or Plasma','ng/mL','ng/mL',''),
  ('SED RATE BY MODIFIED WESTERGREN','SED RATE BY MODIFIED WESTERGREN','4537-7','Erythrocyte sedimentation rate by Westergren method','mm/h','mm/h','')
)
INSERT INTO ingest_portal.code_map_local_to_loinc
  (source, local_code, local_display, loinc_code, loinc_display, src_unit, tgt_unit, comment)
SELECT 'portal', local_code, local_display, loinc_code, loinc_display, src_unit, tgt_unit, comment
FROM x
ON CONFLICT (source, local_code) DO UPDATE
SET loinc_code=EXCLUDED.loinc_code,
    loinc_display=EXCLUDED.loinc_display,
    src_unit=EXCLUDED.src_unit,
    tgt_unit=EXCLUDED.tgt_unit,
    comment=EXCLUDED.comment;
