Critical Labs — FHIR Addendum (v1)

Applies to real lab results (CBC/CMP, troponin, creatinine, etc.) using FHIR R4 resources. Primary resources: Observation (category: laboratory) and DiagnosticReport. Secondary: Specimen, Device, Encounter, Organization. Units are UCUM; tests identified by LOINC.

A. Resource Relationships (ingress model)
DiagnosticReport
  ├─ subject        → Patient
  ├─ effective[x]   (report period; optional)
  ├─ issued         (when report released)
  ├─ performer[]    → Organization/Practitioner
  └─ result[]       → Observation (1..n)
       ├─ status    (preliminary|final|amended|corrected)
       ├─ category  (laboratory)
       ├─ code      (LOINC; display)
       ├─ value[x]  (Quantity|string|CodeableConcept|Ratio|Integer)
       ├─ interpretation[] (HL7 v3 codes: H,L,HH,LL,A,N…)
       ├─ referenceRange[] (low/high, type=normal|critical|therapeutic, appliesTo, age)
       ├─ effective[x] (when measurement applies, often DateTime)
       ├─ issued        (when issued)
       ├─ component[]   (for multi-analyte panels)
       ├─ specimen      → Specimen
       ├─ performer[]   → Organization/Practitioner/Device
       ├─ device        → Device
       └─ hasMember[]   → Observation (panel members referenced separately)


Panels appear in two ways:

Observation.component[] (one resource, many components).

hasMember[] / DiagnosticReport.result[] (many child Observations).

We flatten both into per-metric rows in our canonical series.

B. Canonical Capture (exact fields to persist)
B1. Store raw FHIR (for audit/exports)

raw.fhir_observation (jsonb): verbatim Observation resource.

raw.fhir_diagnosticreport (jsonb): verbatim DR (if provided).

Keep meta (versionId, lastUpdated, tag, security) for audit.

B2. Normalized row(s) per metric (core)

Table: core.lab_result — one row per metric instance (component or atomic observation). Required columns:

Column	Source FHIR path	Notes
person_id	Observation.subject.reference	Resolve to internal person.
encounter_id	Observation.encounter (or DR.encounter)	Optional but useful.
org_id / tenant_id	routing	Multi-tenant.
dr_id	DiagnosticReport.id (if present)	Provenance.
observation_id	Observation.id	Provenance.
identifier	Observation.identifier[]	For dedup.
status	Observation.status	Use final/amended/corrected for analytics.
category	Observation.category[]	Expect laboratory.
loinc_code	Observation.code.coding[?system=LOINC].code	Required.
test_name	Observation.code.text or .coding.display	Human label.
component_code	Observation.component[x].code.coding[LOINC].code	If using component; else null.
metric_key	derived (via ref.lab_metric_map)	Canonical grouping.
value_raw	value[x] or component.value[x]	Stringified.
value_num	valueQuantity.value (parsed)	Null if non-numeric.
unit_raw	`valueQuantity.unit	code`
unit_canonical	derived (UCUM normalize)	See conversions.
value_si	derived (to canonical UCUM)	When convertible.
interpretation	interpretation[].coding[].code	v3 codes: H,L,HH,LL,…
ref_low / ref_high	referenceRange[].low/high.value	Select “normal” range → see Section D.
critical_low / _high	referenceRange[type=critical] or policy	If not present, use policy table.
collected_time	Specimen.collection.collected[x] or effective	Best effort.
t_utc (result time)	prefer issued, else effective[x]	Store UTC.
t_local	derived (person/org TZ)	For UI.
method	`method.text	coding`
device_id	device.identifier	Analyzer provenance.
performer	`performer[].display	reference`
notes	note[].text	Narrative.
payload	full Observation (jsonb)	Redundant storage OK for fast reads.
ingested_at	system	ETL timestamp.

For component observations, set loinc_code to the component LOINC, not the parent code; keep parent observation_id in a linkage column (e.g., parent_observation_id).

C. Transformations (FHIR → canonical)

Identify metric(s):

If component[] exists → emit one row per component using that component’s code/value.

Else → emit one row for the Observation itself.

Optionally, if hasMember[]/DR.result[] points to children Observations, fetch/flatten those as well.

LOINC & metric key:

Choose the LOINC from coding[system==http://loinc.org].

Map to metric_key using ref.lab_metric_map. If unmapped, create a fallback metric_key=loinc:{code} (still chartable).

Units & UCUM:

Read UCUM from valueQuantity.system==http://unitsofmeasure.org (code or unit).

Normalize → unit_canonical and convert numeric → value_si when possible (use ref.ucum_conversions).

Reference ranges:

Prefer referenceRange where type is absent or explicitly “normal” (FHIR: ObservationReferenceRangeMeaning).

If multiple ranges exist, choose one that matches appliesTo (e.g., sex) and age.

If not present, fall back to ref.lab_reference_ranges (loinc × sex × age-band).

Critical thresholds:

If the lab supplies a referenceRange with type=critical → use its bounds.

Otherwise consult ref.lab_critical_policy by metric_key (or by LOINC).

Abnormal flags:

Use interpretation[].coding[].code (HL7 v3: H,L,HH,LL,A,N, …). Persist raw codes; also derive is_critical if value crosses critical bounds.

Timestamps:

Result time: prefer Observation.issued; else effectiveDateTime/effectiveInstant/effectivePeriod.end; store as t_utc.

Derive t_local using the person/org TZ at that instant (store TZ id for reproducibility).

Versioning & de-dup:

Natural key candidates: (person_id, loinc/component loinc, t_utc, value_raw) plus Observation.identifier[] if present.

Only analytics-eligible statuses: final, amended, corrected.

If the same natural key re-appears with a newer meta.versionId or issued, supersede the older row; copy old to core.lab_result_history.

D. Choosing the Right Reference Range in FHIR

FHIR allows multiple referenceRange[]. Apply this selector:

Filter by type: prefer none/“normal”; capture critical separately.

Filter by appliesTo that matches patient sex or context.

If age present (Range), compute age on t_utc and pick matching band.

If still multiple, pick the first (but log a warning/flag).

Persist both:

Chosen normal range → ref_low, ref_high

Critical range (from type=critical) → critical_low, critical_high (if present)

E. Aggregations (unchanged, but FHIR-aware)

Materialized views remain as defined, but use canonicalized fields:

analytics.mv_hourly_labs(person_id, metric_key, t_utc_bucket_hour, count, min, max, avg, last_value, flags_any_critical, flags_any_abnormal)

analytics.mv_daily_labs(person_id, metric_key, t_utc_bucket_day, count, min, max, median, p95, last_value, flags_any_critical)

ETL versioning: bump analytics.etl_state.etl_version when:

new FHIR bundles backfilled

policy tables change (reference ranges / critical thresholds)

unit conversions updated

F. API Contracts (FHIR-friendly)
F1. Series for charts (unchanged shape)

GET /labs/{person_id}/critical-series?metrics=potassium,creatinine&agg=daily|hourly

Backend should flatten FHIR component/hasMember into the unified series.

Always include {t_utc, t_local, v, abn, crit, unit, ref_low, ref_high, critical_low, critical_high, agg, tz}.

F2. FHIR export (new)

GET /fhir/Observation/{id} → return stored verbatim Observation.

GET /fhir/DiagnosticReport/{id} → return stored verbatim DR.

GET /labs/{person_id}/latest?metrics=...&format=fhir → emit a Bundle of Observations for the latest datapoints.

G. SQL & ETL Notes (pseudocode)
G1. Flatten components
-- Insert atomic observations
INSERT INTO core.lab_result ( ... )
SELECT ... FROM staging.fhir_observation o
WHERE jsonb_typeof(o.resource->'component') IS NULL;

-- Insert components as separate rows
INSERT INTO core.lab_result ( ... loinc_code, value_num, unit_raw, ... parent_observation_id )
SELECT
  ...,
  comp->'code'->'coding'->0->>'code'        AS loinc_code,
  (comp->'valueQuantity'->>'value')::numeric AS value_num,
  COALESCE(comp->'valueQuantity'->>'code', comp->'valueQuantity'->>'unit') AS unit_raw,
  o.resource->>'id' AS parent_observation_id,
  ...
FROM staging.fhir_observation o
CROSS JOIN LATERAL jsonb_array_elements(o.resource->'component') AS comp;

G2. Reference range selection (JSONB)

Pick the best referenceRange[] as per Section D; if none, left join to ref.lab_reference_ranges by (loinc_code, sex, age_band).

H. Validation & Safety

FHIR structure validation: accept any R4 Observation but warn when category != laboratory.

Units: only trust UCUM; if system missing, attempt normalization but flag.

Amendments: when status moves from preliminary → final/amended/corrected, supersede earlier result and bump etl_version.

PHI: never leak Patient content to front-end endpoints; chart APIs carry only time/value/meta.

I. CHANGE_LOG (append-only)

For any change that touches FHIR ingestion or mappings, append an entry in CHANGE_LOG.md:

YYYY-MM-DD HH:MM TZ — <author> — FHIR Labs: <summary>

Affected tables/views, migration id, policy table changes, and whether reprocessing & etl_version bump are required.

J. Coder Checklist (What to implement now)

Staging tables

staging.fhir_observation(resource jsonb, received_at, tenant_id)

staging.fhir_diagnosticreport(resource jsonb, received_at, tenant_id)

Normalizer jobs

Component flattening; hasMember/DR.result dereferencing.

LOINC→metric_key mapping; UCUM normalization; reference range selection; critical policy application.

Timestamp derivation (t_utc/t_local), status gating, dedup/versioning.

Ref data seeds

ref.lab_metric_map, ref.ucum_conversions, ref.lab_reference_ranges, ref.lab_critical_policy.

Aggregates + etl_state

Build/refresh materialized views; set/bump etl_version.

API surface

/labs/{person_id}/critical-series (existing) — confirm FHIR-flattened source.

/labs/{person_id}/latest (if not present).

/fhir/Observation/{id} and /fhir/DiagnosticReport/{id} (read-only passthrough).

Tests

Ingest a FHIR DiagnosticReport with a panel that mixes component[] and individual Observations; assert flattening, units, ranges, and critical flags.

Round-trip FHIR export matches the stored raw resource.