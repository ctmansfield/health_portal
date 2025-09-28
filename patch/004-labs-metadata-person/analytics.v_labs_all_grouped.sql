-- Patch: Correct lab grouping and person-scoped metadata views

-- Drop existing views
DROP VIEW IF EXISTS analytics.v_labs_all_grouped CASCADE;
DROP VIEW IF EXISTS analytics.v_labs_metadata_person CASCADE;

-- Recreate the grouped view with comprehensive lab groupings
CREATE OR REPLACE VIEW analytics.v_labs_all_grouped AS
WITH base AS (
    SELECT
        v.*,
        lower(label) AS label_norm_lc,
        analytics.label_key(label) AS label_key_norm
    FROM analytics.v_labs_all v
),
grouping AS (
    SELECT
        b.*,
        CASE
            WHEN b.label ILIKE ANY (ARRAY[
                '%AMPHETAMINE%', '%BARBITURATE%', '%BENZODIAZEPINE%', '%COCAINE%',
                '%METHADONE%', '%OPIATE%', '%OXYCODONE%', '%CANNABINOID%'
            ]) THEN 'Drug Screen'

            WHEN b.label ILIKE ANY (ARRAY[
                'HIV%', 'HIV-1%', 'CHLAMYDIA%', 'NEISSERIA GONORRHOEA%', 'RPR%', 'HEPATITIS%'
            ]) THEN 'STI Tests'

            WHEN b.label ILIKE '%URINE%' OR b.label IN ('SPECIFIC GRAVITY', 'CLARITY (CBOC)', 'UROBILINOGEN (CBOC)', 'HYALINE CASTS/LPF', 'SQUAMOUS EPI/LPF') THEN 'Urine'

            WHEN b.label IN (
                'WBC','RBC','HGB','Hgb','HCT','Hct','MCV','MCH','MCHC','RDW','RDW-CV','Platelet Count','MPV',
                'NEUTROPHILS %','NEUTROPHILS ABSOLUTE','LYMPHOCYTES %','LYMPHOCYTES ABSOLUTE',
                'MONOCYTES %','MONOCYTES ABSOLUTE','EOSINOPHILS %','EOSINOPHILS ABSOLUTE',
                'BASOPHILS %','BASOPHILS ABSOLUTE','NUCLEATED RBC/100WBC',
                'IMMATURE GRANULOCYTE %','IMMATURE GRANULOCYTES ABS'
            ) THEN 'Complete Blood Count'

            WHEN b.label IN (
                'Cholesterol','CHOLESTEROL TOTAL','Triglycerides','TRIGLYCERIDES','HDL','LDL','LDL Calculated','Chol/HDL Ratio'
            ) THEN 'Lipids'

            WHEN b.label IN (
                'Sodium','SODIUM','Potassium','POTASSIUM','Chloride','CHLORIDE','CO2',
                'BUN','Creatinine','CREATININE','eGFR','Glucose','GLUCOSE',
                'Calcium','CALCIUM','Calcium Corrected for Albumin','Albumin','Protein, Total','PROTEIN TOTAL',
                'Alkaline Phosphatase','ALT','AST','Bilirubin, Total',
                'ANION GAP','CALCULATED OSMOLALITY','CK TOTAL','URIC ACID'
            ) THEN 'Metabolic Panel'

            WHEN b.label IN (
                'TSH','FREE THYROXINE (T4)','CORTISOL (SERUM)','FSH','PROLACTIN','TOTAL TESTOSTERONE','25 OH VITAMIN D','VITAMIN B12','PSA'
            ) THEN 'Endocrine'

            WHEN b.label IN ('FERRITIN','TIBC','IRON') THEN 'Iron Studies'

            WHEN b.label IN ('PROTHROMBIN TIME','INR','PTT') THEN 'Coagulation'

            WHEN b.label IN ('SED RATE (KNOX)') THEN 'Inflammation'

            WHEN b.label IN ('Oxygen Saturation','Heart Rate','Weight','Body Mass Index','Body Surface Area') THEN 'Vitals/Anthropometrics'

            ELSE 'Other'
        END AS group_name,
        CASE
            WHEN b.label ILIKE ANY (ARRAY[
                '%AMPHETAMINE%', '%BARBITURATE%', '%BENZODIAZEPINE%', '%COCAINE%',
                '%METHADONE%', '%OPIATE%', '%OXYCODONE%', '%CANNABINOID%',
                'HIV%', 'HIV-1%', 'CHLAMYDIA%', 'NEISSERIA GONORRHOEA%', 'RPR%', 'HEPATITIS%'
            ]) THEN TRUE
            ELSE FALSE
        END AS sensitive
    FROM base b
)
SELECT DISTINCT
    person_id,
    label,
    label_norm_lc,
    label_key_norm,
    group_name,
    sensitive
FROM grouping;


-- Create person-scoped metadata view for UI
CREATE OR REPLACE VIEW analytics.v_labs_metadata_person AS
SELECT DISTINCT
    person_id,
    label,
    group_name,
    sensitive
FROM analytics.v_labs_all_grouped;