Critical Labs — Data Dependencies & Transformations (v1)

Scope: real clinical labs (e.g., CBC/CMP, cardiac markers, renal/hepatic, inflammatory markers), not vitals. Targets ingestion from HL7 v2 ORU, FHIR Observation, and CSV; normalizes to a canonical internal shape; computes hourly/daily aggregations and “critical” events; serves UI/API (/labs/{person_id}/critical-series, /labs/{person_id}/latest, etc.).

1) Data Domain & Objectives

Domain: Quantitative lab results using LOINC codes and UCUM units, with lab-supplied reference ranges, abnormal flags, and (when available) critical/panic thresholds.

Goal: Provide accurate, timezone-aware, downsampled series for charts; robust critical-event detection; and consistent unit normalization across sources.

Outcomes:

Reliable UI time series for “Critical Labs” page and dashboard cards.

Consistent API contracts for client rendering and CSV export.

Auditable lineage from raw message → normalized record → aggregates.

2) Source Systems & Dependencies
2.1 Supported Ingress

HL7 v2 ORU^R01 (OBR/OBX/NTE)

FHIR R4 Observation (plus Patient/Encounter/Specimen when available)

Vendor CSV (ad hoc bulk import)

2.2 External Terminologies / Dictionaries

LOINC — test identification (preferred primary key for lab tests).

UCUM — units (canonicalization).

Local lab dictionaries — lab-specific codes or test names → LOINC mapping.

(Optional) Reference Ranges/Rules — if lab does not supply, maintain internal reference table by LOINC × sex × age.

2.3 Internal Dependencies

Person (core.person) — id, DOB, sex at observation.

Encounter/Order (core.encounter, core.order) — link to context when available.

Tenant/Org (core.tenant) — multi-tenant isolation.

ETL state (analytics.etl_state) — versioning and cache invalidation.

Time zone — person-level preferred TZ or org default; fall back to system TZ.

3) Canonical Internal Model (record-level)

Table: core.lab_result (JSONB + columns)
One row per observation (OBX or FHIR Observation).

3.1 Required Fields to Capture (with source mapping)
Field (internal)	Type	HL7 v2 (OBX/OBR/etc.)	FHIR Observation	Required	Notes
person_id	uuid/int	PID	Observation.subject.reference	M	Link to internal person.
encounter_id	uuid/int	PV1/ORC/OBR	Observation.encounter	O	Helpful for episode context.
specimen_id	text	SPM-2/OBR-15	Observation.specimen	O	Preserve if available.
order_id	text	ORC-2/OBR-2	ServiceRequest / basedOn	O	For de-dupe & lineage.
performing_lab	text	OBR-24, OBX-23	performer.display	O	Display & provenance.
loinc_code	text	OBX-3 (CE/CWE: identifier)	Observation.code.coding[].code	M	Primary test identifier.
test_name	text	OBX-3 (text), OBX-4	Observation.code.text OR coding.display	M	Human-readable name.
value_raw	text	OBX-5	valueQuantity.value (or string)	M	Raw value (string).
unit_raw	text	OBX-6 (UCUM)	valueQuantity.unit OR .code (UCUM)	M	Raw UCUM unit (as sent).
value_num	numeric	OBX-5 (if numeric)	valueQuantity.value	M*	Parsed numeric; null if truly non-numeric.
unit_canonical	text	derived	derived (UCUM canonical)	M*	Canonicalized UCUM (e.g., “mmol/L”).
value_si	numeric	derived	derived	M*	Converted to canonical/target SI unit when possible.
ref_low / ref_high	numeric	OBX-7 (parse; “low-high”)	referenceRange.low/high.value	M*	If missing, populate from internal table by LOINC×sex×age.
critical_low/critical_high	numeric	OBX-7 or site policy	internal policy table / config	O	Use if provided; else internal policy.
abnormal_flag	text	OBX-8 (e.g., H,L,HH,LL,A,N)	interpretation.coding (HL7 v3)	O	Keep raw semantics.
status	text	OBX-11	status (final, amended, corrected)	M	De-dupe & versioning.
collected_time	timestamp	SPM-17 / OBR-7 / OBX-14	effectiveDateTime/Period.start	O	When specimen was collected.
result_time (t_utc)	timestamp	OBX-14 / OBR-22	issued	M	Use for time series; store in UTC.
t_local	timestamp	derived (from person TZ)	derived	M	For UI display.
method	text	OBX-17	method.text / coding	O	For QC/interpretation.
device_id	text	OBX-18	device.identifier	O	Analyzer provenance.
comments	text[]	NTE segments	note.text	O	Preserve interpretive comments.
org_id / tenant_id	uuid/int	routing	routing	M	Multi-tenant isolation.
source_payload	jsonb	raw segments	raw resource	M	For audit/debug.
ingested_at	timestamp	system	system	M	ETL timestamp.

* M* = “required unless genuinely not available”; fill from internal dictionaries when missing (e.g., reference ranges).

3.2 Canonical Metric Key

Create metric_key to group multi-code panels into canonical series where clinically sensible:

Example mappings:

Potassium → potassium (LOINC 2823-3 preferred)

Sodium → sodium (LOINC 2951-2)

Creatinine → creatinine (LOINC 2160-0)

Troponin I/T → troponin (multiple LOINC; annotate subtype)

ALT/AST → alt, ast

WBC, Hemoglobin, Platelets, etc.

Keep these in ref.lab_metric_map(loinc_code, metric_key, canonical_unit_ucum, precision, notes) and do not hard-code in application logic.

4) Transformations & Algorithms
4.1 Normalization Pipeline (ingress → core)

Parse source: HL7 (OBX) or FHIR Observation → raw fields.

Identify test: map local test to LOINC; store both (loinc_code + local_code).

Numeric parse: value_raw → value_num when numeric; keep value_raw always.

Unit handling:

Validate unit_raw against UCUM.

Convert to unit_canonical; if convertible, compute value_si.

If not convertible, set unit_canonical = unit_raw and leave value_si = null (but capture).

Reference ranges:

If provided: parse ref_low/ref_high.

Else: look up by loinc_code × sex × age from ref.lab_reference_ranges.

Critical thresholds:

If provided by lab, capture critical_low/high.

Else: consult ref.lab_critical_policy for the metric (institution policy).

Timestamps:

Choose result_time = OBX-14 or issued; store as t_utc (UTC).

Derive t_local using person/org TZ at that time (store tz id on person).

Status & versioning:

Only FINAL/CORRECTED/AMENDED form part of analytics; supersede older results for the same order_id + loinc + time by latest status.

Flags:

Abnormal from OBX-8 (H,L,HH,LL,A,N).

Compute is_critical if value_num crosses critical thresholds; if not provided, derive from policy table.

4.2 Aggregations (analytics)

analytics.mv_hourly_labs (per person × metric_key × hour):

t_utc_bucket_hour, count, min, max, avg, last_value, flags_any_critical, flags_any_abnormal.

analytics.mv_daily_labs (per person × metric_key × day):

t_utc_bucket_day, count, min, max, median, p95, last_value, flags_any_critical.

Maintain ETL watermark/version in analytics.etl_state for cache-busting.

4.3 Critical Event Detection

Point-critical: any observation crossing critical_low or critical_high.

Sustained-critical: N points within M hours (configurable).

Velocity/Delta flags (optional): rapid rise of troponin, potassium jump > X% over Y hours.

Emit into analytics.lab_critical_events(person_id, metric_key, event_time, type, severity, window_start, window_end, details jsonb).

4.4 Unit Conversions (UCUM)

Keep a ref.ucum_conversions(from_ucum, to_ucum, factor, offset) for deterministic conversions (e.g., mg/dL → mmol/L where feasible).

Prefer a single canonical unit per metric_key for charting/export (e.g., Potassium → mmol/L).

4.5 De-duplication & Amendments

De-dupe keys: (person_id, loinc_code, t_utc, value_raw, order_id); keep most recent FINAL/AMENDED by ingested_at.

Preserve prior versions in core.lab_result_history for audit.

5) Storage Layout (Postgres)
raw.lis_message                     -- raw inbound HL7/FHIR/CSV blobs + transport metadata
staging.lab_obs                     -- parsed row-per-OBX/Observation (near 1:1)
core.lab_result                     -- normalized record (columns + payload jsonb)
core.lab_result_history             -- prior versions (for audit/amend)
ref.lab_metric_map                  -- loinc → metric_key, canonical unit, display names
ref.lab_reference_ranges            -- loinc × sex × age_band → ref_low/high (+ method)
ref.lab_critical_policy             -- metric_key (or loinc) → critical_low/high, rules
ref.ucum_conversions                -- deterministic unit conversions

analytics.mv_hourly_labs            -- materialized view (hourly)
analytics.mv_daily_labs             -- materialized view (daily)
analytics.lab_critical_events       -- detected events
analytics.etl_state                 -- watermarks, versions, cache TTL hints


Indexes (representative):

core.lab_result (person_id, metric_key, t_utc) btree

core.lab_result (loinc_code, t_utc) btree

core.lab_result USING gin (source_payload jsonb_path_ops)

Aggregates: (person_id, metric_key, t_utc_bucket_hour/day)

6) API Contracts (UI/Data Contract)
6.1 Critical Series

GET /labs/{person_id}/critical-series?metrics=potassium,creatinine&agg=daily|hourly

Response

[
  {
    "metric": "potassium",
    "unit": "mmol/L",
    "tz": "America/Los_Angeles",
    "agg": "daily",
    "ref_low": 3.5,
    "ref_high": 5.1,
    "critical_low": 2.5,
    "critical_high": 6.5,
    "series": [
      { "t_utc": "2025-09-10T14:00:00Z", "t_local": "2025-09-10T07:00:00-07:00", "v": 5.8, "abn": "H", "crit": true },
      { "t_utc": "...", "t_local": "...", "v": 4.7, "abn": "N", "crit": false }
    ]
  }
]


Notes:

Always include unit, ref_low/high, critical_low/high (if known), and both t_utc and t_local.

For hourly, downsample server-side if > N points (configurable; include downsampled=true in response meta if applied).

6.2 Latest Snapshot

GET /labs/{person_id}/latest?metrics=...

Response

{
  "tz": "America/Los_Angeles",
  "metrics": [
    {
      "metric": "creatinine",
      "unit": "mg/dL",
      "value": 2.1,
      "abn": "H",
      "crit": false,
      "t_utc": "2025-09-10T12:01:00Z",
      "t_local": "2025-09-10T05:01:00-07:00",
      "ref_low": 0.6,
      "ref_high": 1.3
    }
  ]
}

7) “Critical” Metrics — Starter Set

Keep the authoritative list in ref.lab_metric_map (and expand safely). Below are common, high-signal metrics to seed:

Electrolytes: potassium, sodium, chloride, CO₂/bicarbonate, calcium (total/ionized), magnesium, phosphate

Renal: creatinine, BUN, eGFR (derived)

Hepatic: AST, ALT, ALP, total bilirubin, albumin

Hematology: hemoglobin, hematocrit, WBC, platelets, MCV

Cardiac: troponin (I/T subtype), BNP/NT-proBNP

Metabolic: glucose, lactate, ketones

Coagulation: INR, PT, aPTT, D-dimer

Inflammatory: CRP, ESR

Other high-alerts (site policy): digoxin level, lithium level, valproate level (therapeutic drug monitoring)

For each, define in ref.lab_metric_map:

loinc_code, metric_key, display_name, canonical_unit_ucum, precision, panel (if applicable), notes.

8) Caching & Invalidation

Redis preferred (fallback to in-process cache). Keys include:

labs:series:{person_id}:{agg}:{metric_key}:{etl_version}

labs:latest:{person_id}:{etl_version}

etl_version from analytics.etl_state (increment on refresh/amend).

TTL: short for hourly (e.g., 1–5 min), longer for daily (e.g., 30–60 min).

Bust cache on message ingress with FINAL/CORRECTED status or if critical policy changes.

9) Data Quality & Safety Rails

Unit sanity checks: alert on unexpected UCUM or out-of-range values (e.g., mg/dL where mmol/L expected).

Age/sex-aware ranges: compute on the observation date (patient ages over time).

Amendment handling: supersede prior in aggregates; keep history.

Time monotonicity: guard against clock skew; prefer result_time over received_at.

Multi-tenant isolation: org_id column on all tables; row-level security if enabled.

PHI: never emit PHI in logs/JS; ensure API auth on /labs/*.

10) UI/UX Contract (what front-end expects)

Time series points: {t_utc, t_local, v, abn, crit}.

Series metadata: {metric, unit, ref_low, ref_high, critical_low, critical_high, agg, tz}.

Bands: front-end shows reference bands using ref_low/ref_high (and optional critical_*).

Accessibility: series named by metric, aria-label on canvases; CSV export provided by API or client transform.

11) Operational Runbooks (quick)

Backfill: bulk import CSV → staging → core; re-run aggregates; bump etl_version.

Reprocess policy change: when ref.lab_critical_policy updates, re-evaluate is_critical and events; bump etl_version.

Hotfix bad units: update ref.ucum_conversions or ref.lab_metric_map; re-run affected conversions.

12) Implementation Order (coder-ready)

Ref tables & mappings

Seed ref.lab_metric_map, ref.ucum_conversions, ref.lab_reference_ranges, ref.lab_critical_policy.

Ingestion mappers

HL7→staging→core; FHIR→staging→core; CSV→staging→core.

Normalization functions

Unit conversion (UCUM), reference-range resolver (by loinc×sex×age), critical-flag evaluator.

Aggregates

Build/refresh mv_hourly_labs, mv_daily_labs; maintain etl_state.

Critical events

Implement sustained-crit detection; write analytics.lab_critical_events.

API

/labs/{person_id}/critical-series (hourly/daily + downsampling), /labs/{person_id}/latest.

UI

Wire charts to API; show bands; CSV export; toolbar (agg toggle, preview/live).

13) Field-by-Field Capture Matrix (condensed)

Identity & context

person_id, encounter_id, specimen_id, order_id, org_id/tenant_id

Test identification

loinc_code, test_name, local_test_code (if any), metric_key

Value & units

value_raw, value_num, unit_raw, unit_canonical, value_si, precision

Ranges & flags

ref_low, ref_high, critical_low, critical_high, abnormal_flag, is_critical

Timing

collected_time, result_time(t_utc), t_local, timezone_id

Provenance

performing_lab, method, device_id, status, comments[], source_payload, ingested_at

14) Notes on Codes & Portability

LOINC and UCUM are the durable keys for portability across systems.

Keep local code → LOINC mapping in ref.lab_metric_map so you can ingest diverse feeds without code changes.

Keep policy (critical thresholds) in data, not code, so sites can vary policy without redeploying.

15) Change Management

Never overwrite existing CHANGE_LOG.md.

For any schema or transformation change, append an entry:

Date/time, author, brief summary, affected tables/views, migration id, API change notes.

For high-impact changes (e.g., critical policy), include a one-liner on required reprocessing and whether etl_version must be bumped.
Observe FHIR data structure standards.
