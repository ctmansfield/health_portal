FHIR End-to-End Ingest — Data Model, Transforms, and Required Fields (v1)

Goal: Accept broad FHIR R4 clinical data (labs, imaging, notes, observations, medications, conditions, procedures, etc.), store verbatim payloads for audit/export, and normalize core data into analytics-ready tables — all multi-tenant, append-safe, and replayable. All timestamps stored in UTC with person-local projections for UI.

0) Scope & Tenets

Resources in scope (R4): Patient, Encounter, Practitioner, Organization, Location, Observation (laboratory, vital-signs, imaging measurements), DiagnosticReport, ImagingStudy, DocumentReference, Binary (by reference), Condition, Procedure, MedicationRequest, MedicationStatement, AllergyIntolerance, ServiceRequest, Specimen, Device, Provenance.

Storage pattern: (1) staging (verbatim JSONB) → (2) core (normalized, queryable) → (3) analytics (materialized views).

Versioning & dedup: Prefer resource.id + meta.versionId; fall back to identifier[system,value]. Never hard-delete. Keep history in *_history.

Attachments: Store references to binaries in object storage (filesystem/S3) with checksum & contentType; never inline big blobs in DB.

Profiles/validation: Accept any valid R4; optionally validate against local profiles (deferred). Reject malformed; quarantine instead of dropping.

1) Tables (overview)
1.1 Staging (verbatim FHIR, append-only)

staging.fhir_patient(resource jsonb, received_at timestamptz, tenant_id text, source text)

staging.fhir_encounter(...)

staging.fhir_practitioner(...)

staging.fhir_organization(...)

staging.fhir_observation(...)

staging.fhir_diagnosticreport(...)

staging.fhir_imagingstudy(...)

staging.fhir_documentreference(...)

staging.fhir_condition(...)

staging.fhir_procedure(...)

staging.fhir_medicationrequest(...)

staging.fhir_medicationstatement(...)

staging.fhir_allergyintolerance(...)

staging.fhir_servicerequest(...)

staging.fhir_specimen(...)

staging.fhir_device(...)

staging.fhir_provenance(...)

Required staging columns for all:
resource jsonb NOT NULL, received_at timestamptz NOT NULL DEFAULT now(), tenant_id text NOT NULL, source text NULL

1.2 Identity Map (references → internal IDs)

core.ref_identity (tenant_id, resource_type, fhir_id, identifier_system, identifier_value, internal_id uuid, last_seen timestamptz, UNIQUE(tenant_id, resource_type, fhir_id))

1.3 Core normalized (one row per “thing”)

Patient/Provider/Org

core.person (person_id uuid PK, tenant_id, fhir_id, mrn text[], birth_date date, deceased boolean, sex text, name text, telecom jsonb, address jsonb, payload jsonb, updated_at)

core.practitioner (prac_id uuid, tenant_id, fhir_id, name text, identifiers jsonb, payload jsonb, updated_at)

core.organization (org_id uuid, tenant_id, fhir_id, name text, identifiers jsonb, payload jsonb, updated_at)

core.encounter (enc_id uuid, tenant_id, fhir_id, person_id, period_start timestamptz, period_end timestamptz, class text, type jsonb, reason jsonb, payload jsonb)

Observations (generalized + specializations)

core.observation_flat — one row per atomic value (Observation or component):

tenant_id, person_id, enc_id, obs_id text, parent_obs_id text, category text, loinc_code text, code_display text, value_type text, value_num numeric, value_str text, unit_raw text, unit_ucum text, value_si numeric, interpretation text[], ref_low numeric, ref_high numeric, effective_time timestamptz, issued_time timestamptz, device_id text, performer jsonb, status text, method text, spec_ref text, payload jsonb, ingested_at timestamptz

Note: labs specialization core.lab_result can view or inherit from this (see Lab addendum).

Imaging

core.imaging_study_index

tenant_id, person_id, study_uid text, accession text, modality_list text[], started_at timestamptz, series_count int, instance_count int, body_site text, laterality text, referrer_practitioner text, endpoint_urls jsonb, payload jsonb

core.imaging_series_index

tenant_id, study_uid, series_uid text, modality text, body_site text, instance_count int, first_seen timestamptz, payload jsonb

core.imaging_instance_index

tenant_id, study_uid, series_uid, sop_uid text, instance_url text, thumbnail_url text, size_bytes bigint, checksum_sha256 bytea, content_type text

Diagnostic Reports (all domains: lab, imaging, pathology, cardiology)

core.diagnostic_report_index

tenant_id, dr_id text, person_id, category text[], code text, code_system text, code_display text, status text, effective_start timestamptz, effective_end timestamptz, issued timestamptz, performer jsonb, result_obs_ids text[], imaging_study_refs text[], payload jsonb

Documents & Notes

core.document_index

tenant_id, doc_id text, person_id, encounter_id, type_code text, type_system text, type_display text, category text[], author jsonb, created timestamptz, indexed timestamptz, status text, content_count int, payload jsonb

core.document_content (one row per attachment in DocumentReference.content[])

tenant_id, doc_id text, attachment_index int, content_type text, title text, size_bytes bigint, hash_sha256 bytea, lang text, url text, storage_key text, storage_bucket text, storage_region text, created timestamptz

Clinical Coding Sets

core.condition

tenant_id, cond_id text, person_id, onset_time timestamptz, abatement_time timestamptz, clinical_status text, verification_status text, code text, code_system text, code_display text, category text[], severity text, body_site jsonb, recorder jsonb, asserter jsonb, payload jsonb

core.procedure

tenant_id, proc_id text, person_id, performed_start timestamptz, performed_end timestamptz, code text, code_system text, code_display text, status text, category text[], body_site jsonb, performer jsonb, payload jsonb

core.medication_request

tenant_id, mr_id text, person_id, authored_on timestamptz, status text, intent text, medication_code text, dose jsonb, route text, reason jsonb, requester jsonb, payload jsonb

core.medication_statement

tenant_id, ms_id text, person_id, effective_time timestamptz, status text, medication_code text, reason jsonb, adherence jsonb, payload jsonb

core.allergy_intolerance

tenant_id, ai_id text, person_id, recorded_date timestamptz, clinical_status text, verification_status text, code text, code_system text, code_display text, category text[], criticality text, reaction jsonb, payload jsonb

Attachments (object store index)

core.blob_store

tenant_id, storage_key text PK, content_type text, size_bytes bigint, sha256 bytea, created timestamptz, last_access timestamptz, url_public text NULL

Audit

core.provenance_index (tenant_id, target_type, target_id, recorded timestamptz, agents jsonb, signature jsonb, payload jsonb)

core._etl_state (key text PK, value jsonb, updated_at)

2) Transforms (by resource)
2.1 Patient / Encounter / Organization / Practitioner

Resolve identity: Patient.identifier[] (MRN systems) + resource.id → core.ref_identity.

Capture fields: birthDate, gender/sex, name[], telecom[], address[].

Encounter: class, type[], period, reasonCode[]/reasonReference[].

2.2 Observation (general)

Flatten Observation into atomic rows:

If component[] exists, emit one row per component (use component’s code, value[x]).

Otherwise, one row per Observation.

Units: prefer UCUM (valueQuantity.system == unitsofmeasure.org); normalize to unit_ucum; derive value_si using conversion table.

Timing: effective[x] (prefer) or issued.

Ranges/Flags: store interpretation[]; select referenceRange (normal vs critical) as in the Labs addendum.

2.3 DiagnosticReport (all domains)

Store verbatim JSON; index: category, code, status, issued, and pointers to result[] (Observation ids) and imagingStudy[].

For lab DRs, the Observations drive the numeric time-series; DR provides provenance & cohort context.

2.4 ImagingStudy (DICOM indexing)

From ImagingStudy, compute series_count, instance_count, modalities, started time.

For each Series/Instance, store UIDs and the retrieval URL (WADO-RS or your gateway URL) in core.imaging_instance_index.

Do not store pixel data in DB; store only metadata + pointer.

Optionally generate server-side thumbnails and register in imaging_instance_index.thumbnail_url.

2.5 DocumentReference / Binary (clinical notes, reports, PDFs)

Index document metadata in core.document_index (type, category, author, created, status).

For each content[]:

If attachment.url is remote (http(s)), fetch → store to object store, record storage_key, sha256, size_bytes, contentType.

If attachment.data is inline (base64), decode and store similarly.

Link DocumentReference.context.encounter and subject.

2.6 Condition / Procedure / Medications / Allergies

Map CodeableConcept codings (SNOMED, ICD-10-CM, CPT, RxNorm).

Persist both primary code (pick a preferred system) and full codings[] in payload to prevent information loss.

2.7 Specimen / Device / ServiceRequest

Specimen: type, collection.collected[x], bodySite, container[], identifier[] (to link labs to exact tube/sample).

Device: udiCarrier.deviceIdentifier, type, identifier[] (instrument provenance).

ServiceRequest: ordering context for labs/imaging; link to DR via basedOn[] where present.

3) Required Fields to Capture (per resource)

Below are must-capture fields (minimum viable set). Everything else remains in payload jsonb.

Patient

person_id, tenant_id, fhir_id, identifiers (array of {system,value}), birth_date, sex, name.display, telecom, address, payload

Encounter

enc_id, tenant_id, fhir_id, person_id, period_start, period_end, class, type[], reason[], payload

Observation (atomic/component)

tenant_id, person_id, enc_id, obs_id, parent_obs_id?, category, loinc_code, code_display, value_type, value_num, value_str, unit_raw, unit_ucum, value_si, interpretation[], ref_low, ref_high, effective_time, issued_time, device_id?, status, method?, spec_ref?, payload

DiagnosticReport

tenant_id, dr_id, person_id, category[], code, code_system, code_display, status, effective_start, effective_end, issued, performer, result_obs_ids[], imaging_study_refs[], payload

ImagingStudy / Series / Instance

Study: tenant_id, person_id, study_uid, accession?, modality_list[], started_at, series_count, instance_count, body_site?, payload

Series: tenant_id, study_uid, series_uid, modality, body_site?, instance_count, payload

Instance: tenant_id, study_uid, series_uid, sop_uid, instance_url, thumbnail_url?, size_bytes?, checksum_sha256?, content_type?

DocumentReference / Content

Doc: tenant_id, doc_id, person_id, encounter_id?, type_code, type_system, type_display, category[], author, created, indexed, status, content_count, payload

Content: tenant_id, doc_id, attachment_index, content_type, title, size_bytes, hash_sha256, lang?, url?, storage_key, storage_bucket, storage_region?, created

Condition

tenant_id, cond_id, person_id, clinical_status, verification_status, code, code_system, code_display, onset_time?, abatement_time?, category[], severity?, body_site?, payload

Procedure

tenant_id, proc_id, person_id, status, code, code_system, code_display, performed_start?, performed_end?, category[], body_site?, performer?, payload

MedicationRequest / MedicationStatement

MR: tenant_id, mr_id, person_id, status, intent, authored_on, medication_code, dose jsonb, route?, reason?, requester?, payload

MS: tenant_id, ms_id, person_id, status, effective_time?, medication_code, reason?, adherence?, payload

AllergyIntolerance

tenant_id, ai_id, person_id, recorded_date?, clinical_status, verification_status, code, code_system, code_display, category[], criticality?, reaction jsonb, payload

Specimen

tenant_id, specimen_id, person_id, type?, body_site?, collected_time?, identifier[], container[], payload

Device

tenant_id, device_id, udi_device_identifier?, type?, identifier[], payload

4) Dedup, Versioning, and History

Primary key per external resource: (tenant_id, resource_type, fhir_id); store meta.versionId/meta.lastUpdated.

On ingest:

If new (tenant_id, type, fhir_id) → insert.

If same id with higher version → supersede: update current, move old to *_history.

Also consider identifier pairs for systems that don’t reuse resource.id across sources.

Natural keys (for Observations): (person_id, loinc/component, effective_time, value_raw) for rough dup detection; prefer FHIR identifiers when present.

5) Analytics Views (examples)

analytics.mv_daily_vitals (existing) — keep.

analytics.mv_daily_labs — rollup from core.observation_flat where category='laboratory' and numeric values.

analytics.mv_latest_documents — per person & type_code.

analytics.mv_imaging_counts — counts per modality/day.

All analytics should track etl_version from core._etl_state so front-ends can cache-bust safely.

6) Attachments & File Storage

Configure HP_BLOB_STORE for filesystem://path or s3://bucket/prefix.

On DocumentReference.content[] or Binary links:

If url http(s) → download (if allowed), set storage_key, compute sha256.

If data inline → decode and store.

Never store >20MB blobs in DB; only store metadata + pointer.

7) API Surfaces (read-only, minimal write)

FHIR passthrough (read):

GET /fhir/{type}/{id} → return verbatim payload.

Series & search:

GET /labs/{person_id}/critical-series?... (already implemented; ensure it reads from core.observation_flat).

GET /observations/{person_id}?category=vital-signs|laboratory&code=...&since=... → generic series.

GET /documents/{person_id}?type=XX → index; GET /documents/{doc_id}/content/{i} → redirect to signed URL.

GET /imaging/{person_id}/studies → index; GET /imaging/studies/{study_uid} → series/instances + WADO links.

(Write endpoints for ingest can be CLI/ETL jobs for now, not public HTTP.)

8) ETL Flow (NDJSON or Bundle)

Drop FHIR NDJSON/Bundles to /data/incoming/<tenant>/<yyyymmdd>/.

etl/fhir_ingest.py:

Validate minimal resource shape (resourceType, id).

Insert into staging.fhir_*.

Upsert identity to core.ref_identity.

Normalize tasks (idempotent):

Patients/Encounters/Orgs first → resolve person_id, enc_id.

Observations → flatten (incl. components), normalize units, select ref ranges.

DR → index pointers.

ImagingStudy → series & instances indices (no pixel data).

DocumentReference → content fetch/store.

Conditions/Procedures/Medications/Allergies → index codes.

Analytics refresh (materialized views).

Bump core._etl_state.etl_version (json: {labs: N, imaging: N, docs: N, obs: N}).

9) Indices & Performance

GIN on payload for ad-hoc queries (jsonb_path_ops).

B-tree on:

core.observation_flat(person_id, loinc_code, effective_time)

core.diagnostic_report_index(person_id, issued)

core.document_index(person_id, created)

core.imaging_study_index(person_id, started_at)

Partial index: WHERE value_num IS NOT NULL for observation numerics.

10) Security & PHI

Never log payloads; log only resource ids.

Encrypt object store at rest; prefer signed URLs (short TTL) for downloads.

Field-level redaction for patient-facing UIs (e.g., hide author names on notes if policy requires).

11) CHANGE_LOG (append-only)

Never overwrite. Always append entries at repo root CHANGE_LOG.md.

Template line:

YYYY-MM-DD HH:MM TZ — <author> — FHIR ingest: <component> — <summary>; affects <tables/views>; etl_version +1 (<component>)

12) Coder Checklist (next actions)

Create staging tables for all resources listed in §1.1.

Implement identity map upsert (core.ref_identity) on ingest.

Build normalizers:

obs_normalize() → fills core.observation_flat (uses UCUM conversions + ref range selection).

dr_indexer() → fills core.diagnostic_report_index.

imaging_indexer() → fills study/series/instance tables (no pixel data).

doc_fetcher() → stores attachments to object store, fills core.document_content.

codes_indexer() → condition/procedure/medications/allergies.

Add analytics views (mv_daily_labs, mv_imaging_counts, mv_latest_documents).

Wire APIs for read endpoints in §7 (backed by normalized tables).

Tests:

NDJSON fixture with: one ImagingStudy + DocumentReference(PDF) + DR(lab) + mixed Observation components + Condition/Medication.

Assert identity resolution, observation flattening, document storage, imaging indexing, and series API output.

Docs: append a CHANGE_LOG entry; update docs/data/ with any profile constraints you adopt.

13) Appendix — UCUM & Code Systems

Units (UCUM): prefer valueQuantity.system == "http://unitsofmeasure.org"; table ref.ucum_conversions(from_code, to_code, factor, offset).

Codes:

Labs/Obs: LOINC; Vital signs: LOINC + category vital-signs

Conditions: SNOMED CT (preferred), ICD-10-CM (billing)

Procedures: CPT/SNOMED

Medications: RxNorm

Allergies: SNOMED, RxNorm (substance/agent)

Imaging modalities: DICOM codes (Modality), map to friendly labels.

If you want, I can follow up with:

DDL skeletons for all tables above (Postgres),

a referenceRange selector SQL function, and

a minimal Python NDJSON ingester stub you can wire into your ETL.