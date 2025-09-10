-- Helpful partial indexes for vitals
CREATE INDEX IF NOT EXISTS idx_events_loinc_hr_time
  ON analytics.data_events(effective_time)
  WHERE code_system='LOINC' AND code='8867-4' AND value_num IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_events_loinc_spo2_time
  ON analytics.data_events(effective_time)
  WHERE code_system='LOINC' AND code='59408-5' AND value_num IS NOT NULL;

-- Simple day-floor SQL function (UTC)
CREATE OR REPLACE FUNCTION analytics.day_floor_utc(ts timestamptz)
RETURNS timestamptz LANGUAGE sql IMMUTABLE AS $$
  SELECT date_trunc('day', ts AT TIME ZONE 'UTC') AT TIME ZONE 'UTC';
$$;
