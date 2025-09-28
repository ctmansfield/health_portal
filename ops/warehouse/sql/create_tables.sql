create table if not exists ref_map (
  ref_uid uuid primary key,
  server_base text not null,
  resource_type text not null,
  fhir_id text not null,
  unique (server_base, resource_type, fhir_id)
);

create table if not exists fhir_resource (
  ref_uid uuid not null references ref_map(ref_uid) on delete cascade,
  version_id text,
  last_updated timestamptz,
  patient_ref text,
  encounter_ref text,
  resource_type text not null,
  effective_at timestamptz,
  status text,
  codes jsonb,
  source_label text,
  resource_json jsonb not null,
  primary key (ref_uid, version_id)
);
create index if not exists fhir_res_type_idx      on fhir_resource(resource_type);
create index if not exists fhir_res_patient_idx   on fhir_resource(patient_ref);
create index if not exists fhir_res_effective_idx on fhir_resource(effective_at);
create index if not exists fhir_res_codes_gin     on fhir_resource using gin (codes jsonb_path_ops);
create index if not exists fhir_res_json_gin      on fhir_resource using gin (resource_json jsonb_path_ops);

create table if not exists obs_rollup (
  ref_uid uuid primary key references ref_map(ref_uid) on delete cascade,
  fhir_id text, patient_ref text not null,
  code_system text, code text, name text, category text,
  issued_at timestamptz, effective_at timestamptz,
  val_num numeric, val_unit text, val_str text,
  components jsonb, ref_range jsonb
);
create index if not exists obs_patient_time_idx on obs_rollup(patient_ref, effective_at);
create index if not exists obs_code_idx        on obs_rollup(code, code_system);

create table if not exists med_stmt_rollup (
  ref_uid uuid primary key references ref_map(ref_uid) on delete cascade,
  fhir_id text, patient_ref text not null,
  rx_system text, rx_code text, med_text text, status text,
  start_time timestamptz, end_time timestamptz, last_filled timestamptz,
  note text, info_source text
);
create index if not exists meds_patient_idx on med_stmt_rollup(patient_ref, start_time);

create table if not exists condition_rollup (
  ref_uid uuid primary key references ref_map(ref_uid) on delete cascade,
  fhir_id text, patient_ref text not null,
  code_system text, code text, display text,
  clinical_status text, verification text,
  onset_at timestamptz, abatement_at timestamptz
);
create index if not exists cond_patient_idx on condition_rollup(patient_ref, onset_at);
