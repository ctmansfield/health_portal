# Design Brief — FHIR-first Core + Critical Labs + Browse
- Schemas: ref.*, clinical.*, imaging.*, analytics.*
- Importer: FHIR Bundle → clinical.lab_result / clinical.clinical_note / imaging.imaging_study (+ analytics.observation_flat mirror)
- MV: analytics.mv_critical_labs with low/high critical flags from ref.loinc_critical_ranges
- APIs: /labs/{person}/critical-series, /records/* browse
- CHANGE_LOG.md is append-only (never overwritten).
