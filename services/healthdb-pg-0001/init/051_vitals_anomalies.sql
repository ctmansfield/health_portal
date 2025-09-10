-- Normalize SpO2 to 0..1, tolerating 0..100 inputs
CREATE OR REPLACE VIEW analytics.v_spo2_normalized AS
SELECT person_id,
       effective_time,
       CASE
         WHEN value_num IS NULL THEN NULL
         WHEN value_num > 1.5 THEN value_num/100.0
         ELSE value_num
       END AS spo2_norm,
       meta
FROM analytics.data_events
WHERE code_system='LOINC' AND code='59408-5';

-- Flag suspicious vitals for quick eyeballing
CREATE OR REPLACE VIEW analytics.v_vitals_anomalies AS
WITH hr_bad AS (
  SELECT person_id, effective_time, code, value_num, 'hr_out_of_range'::text AS reason
  FROM analytics.data_events
  WHERE code_system='LOINC' AND code='8867-4'
    AND (value_num < 20 OR value_num > 220)
),
spo2_bad AS (
  SELECT person_id, effective_time, '59408-5'::text AS code, value_num, 'spo2_gt_1_5'::text AS reason
  FROM analytics.data_events
  WHERE code_system='LOINC' AND code='59408-5' AND value_num > 1.5
)
SELECT * FROM hr_bad
UNION ALL
SELECT * FROM spo2_bad
ORDER BY effective_time DESC;
