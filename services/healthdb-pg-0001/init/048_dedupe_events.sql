WITH d AS (
  SELECT id,
         person_id, code_system, code, effective_time,
         ROW_NUMBER() OVER (
           PARTITION BY person_id, code_system, code, effective_time
           ORDER BY id DESC
         ) AS rn
  FROM analytics.data_events
  WHERE value_num IS NOT NULL
    AND code_system IS NOT NULL
    AND code IS NOT NULL
    AND effective_time IS NOT NULL
)
DELETE FROM analytics.data_events e
USING d
WHERE e.id = d.id
  AND d.rn > 1;
