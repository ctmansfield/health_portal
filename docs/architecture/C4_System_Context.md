# C4 — System Context

```mermaid
flowchart LR
  Patient((Patient)) ---|views| Dashboard[health_portal Dashboard]
  Clinician((Clinician)) ---|views| Dashboard
  Dashboard -.->|HTTP (OpenAPI v1)| App[Application Layer]
  App -.->|SQL (least-privilege)| DB[(Postgres)]
  Pipelines[genomics_stack] -.->|emit report.v1.json| App
  ExternalFHIR[(FHIR Systems)] -.->|bundles| App
  ExternalTrials[(ClinicalTrials.gov)] -.->|links only in v0.1| App
```
**Scope**: Dashboard consumes the App; App is the *only* DB client; pipelines emit canonical JSON.
