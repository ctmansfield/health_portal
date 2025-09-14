-- FHIR-ready core + analytics scaffolding
CREATE SCHEMA IF NOT EXISTS ref;
CREATE SCHEMA IF NOT EXISTS clinical;
CREATE SCHEMA IF NOT EXISTS imaging;
CREATE SCHEMA IF NOT EXISTS analytics;

CREATE TABLE IF NOT EXISTS ref.loinc_critical_ranges(
  loinc_code   text PRIMARY KEY,
  metric_name  text NOT NULL,
  unit         text,
  low_critical numeric,
  high_critical numeric,
  ref_low      numeric,
  ref_high     numeric,
  updated_at   timestamptz DEFAULT now()
);

CREATE TABLE IF NOT EXISTS clinical.lab_panel(
  id          bigserial PRIMARY KEY,
  person_id   text,
  panel_code  text,
  panel_name  text,
  reported_at timestamptz,
  source      text
);

CREATE TABLE IF NOT EXISTS clinical.lab_result(
  id            bigserial PRIMARY KEY,
  person_id     text,
  panel_id      bigint REFERENCES clinical.lab_panel(id) ON DELETE SET NULL,
  loinc_code    text,
  test_name     text,
  value_num     numeric,
  value_text    text,
  unit          text,
  observed_at   timestamptz,
  status        text,
  interpretation text,
  ref_low       numeric,
  ref_high      numeric,
  raw_json      jsonb,
  created_at    timestamptz DEFAULT now()
);

CREATE TABLE IF NOT EXISTS analytics.observation_flat(
  id        bigserial PRIMARY KEY,
  person_id text,
  metric    text NOT NULL,        -- e.g., 'hr','spo2','glucose'
  t_utc     timestamptz NOT NULL,
  t_local   timestamptz,
  tz        text,
  value_num numeric,
  source    text,
  raw_json  jsonb
);

CREATE TABLE IF NOT EXISTS clinical.clinical_note(
  id          bigserial PRIMARY KEY,
  person_id   text,
  note_type   text,
  authored_at timestamptz,
  title       text,
  text        text,
  raw_json    jsonb
);

CREATE TABLE IF NOT EXISTS imaging.imaging_study(
  id          bigserial PRIMARY KEY,
  person_id   text,
  study_uid   text UNIQUE,
  modality    text,
  started_at  timestamptz,
  description text,
  raw_json    jsonb
);

CREATE TABLE IF NOT EXISTS imaging.imaging_series(
  id           bigserial PRIMARY KEY,
  study_id     bigint REFERENCES imaging.imaging_study(id) ON DELETE CASCADE,
  series_uid   text,
  body_part    text,
  modality     text,
  num_instances int,
  raw_json     jsonb
);

CREATE TABLE IF NOT EXISTS imaging.imaging_instance(
  id          bigserial PRIMARY KEY,
  series_id   bigint REFERENCES imaging.imaging_series(id) ON DELETE CASCADE,
  sop_uid     text,
  instance_no int,
  content_uri text,
  size_bytes  bigint,
  raw_json    jsonb
);

CREATE INDEX IF NOT EXISTS idx_lab_result_person_time ON clinical.lab_result(person_id, observed_at);
CREATE INDEX IF NOT EXISTS idx_obs_flat_person_time  ON analytics.observation_flat(person_id, t_utc);
CREATE INDEX IF NOT EXISTS idx_loinc_metric          ON ref.loinc_critical_ranges(loinc_code, metric_name);
