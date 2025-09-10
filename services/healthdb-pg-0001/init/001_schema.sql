set timezone to 'UTC';
CREATE SCHEMA IF NOT EXISTS fhir_raw;
CREATE SCHEMA IF NOT EXISTS analytics;

CREATE TABLE IF NOT EXISTS fhir_raw.resources (
  resource_type text NOT NULL,
  resource_id   text NOT NULL,
  resource      jsonb NOT NULL,
  imported_at   timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT fhir_raw_resources_pk PRIMARY KEY (resource_type, resource_id)
);
CREATE INDEX IF NOT EXISTS fhir_raw_resources_gin  ON fhir_raw.resources USING gin (resource);
CREATE INDEX IF NOT EXISTS fhir_raw_resources_type ON fhir_raw.resources (resource_type);

CREATE TABLE IF NOT EXISTS analytics.data_events (
  id bigserial PRIMARY KEY,
  person_id       text NOT NULL,
  source          text NOT NULL,
  kind            text NOT NULL,
  code_system     text,
  code            text,
  display         text,
  effective_time  timestamptz,
  effective_start timestamptz,
  effective_end   timestamptz,
  value_num       double precision,
  value_text      text,
  unit            text,
  device_id       text,
  status          text,
  raw             jsonb NOT NULL,
  meta            jsonb
);
CREATE INDEX IF NOT EXISTS de_person_time   ON analytics.data_events (person_id, effective_time);
CREATE INDEX IF NOT EXISTS de_person_period ON analytics.data_events (person_id, effective_start, effective_end);
CREATE INDEX IF NOT EXISTS de_code          ON analytics.data_events (code_system, code);
CREATE INDEX IF NOT EXISTS de_raw_gin       ON analytics.data_events USING gin (raw jsonb_path_ops);

CREATE TABLE IF NOT EXISTS analytics.person (
  person_id text PRIMARY KEY,
  tz text NOT NULL DEFAULT 'America/New_York'
);
INSERT INTO analytics.person(person_id) VALUES ('me')
ON CONFLICT (person_id) DO NOTHING;

CREATE TABLE IF NOT EXISTS analytics.etl_state (
  key text PRIMARY KEY,
  value text
);
