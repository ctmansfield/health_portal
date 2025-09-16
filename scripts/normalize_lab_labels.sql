-- Normalize 'Alkaline Phosphatase' variants
UPDATE analytics.v_labs_all
SET label = 'alkaline phosphatase'
WHERE LOWER(label) IN ('alkaline phosphatase', 'alkaline phosphatase bilirubin', 'alkaline phosphatase, bilirubin total');

-- Normalize 'Bilirubin, Total' variants
UPDATE analytics.v_labs_all
SET label = 'bilirubin total'
WHERE LOWER(label) IN ('bilirubin total', 'bilirubin, total');

-- Normalize Hemoglobin A1C variants
UPDATE analytics.v_labs_all
SET label = 'hemoglobin a1c'
WHERE LOWER(label) IN ('ha1c', 'hba1c', 'hemoglobin a1c', 'hemoglobin a1c');

-- Add more normalization commands as needed
