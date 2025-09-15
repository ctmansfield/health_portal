Critical Labs — Data Dependencies & Transformations (v1)

[Relocated from repository root; this is the canonical location.]

Scope: real clinical labs (e.g., CBC/CMP, cardiac markers, renal/hepatic, inflammatory markers), not vitals. Targets ingestion from HL7 v2 ORU, FHIR Observation, and CSV; normalizes to a canonical internal shape; computes hourly/daily aggregations and “critical” events; serves UI/API (/labs/{person_id}/critical-series, /labs/{person_id}/latest, etc.).

(Original content preserved below.)

---
