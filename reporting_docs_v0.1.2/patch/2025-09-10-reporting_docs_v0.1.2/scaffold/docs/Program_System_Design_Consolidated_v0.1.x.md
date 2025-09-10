# Health_Portal Genomics Reporting — Program & System Design (v0.1.x) — Consolidated

**Audience:** Engineering, Clinical Informatics, Lab Ops, Compliance, **Practitioners** (MD/DO, DNP, RN, CNA, Nutritionists, Physical Therapists, Personal Trainers), **Researchers**, and **Patient Education** teams

## 1) Executive Summary
We will implement a standards‑aligned reporting capability that unifies oncology CGP and rare‑disease outputs, supports therapy actionability and trial matching, and exports to FHIR / GA4GH formats while remaining audit‑ready. The design favors modularity: data ingress adapters → validation → evidence mapping → storage → rendering → export → audit/compliance.

**Key outcomes**
- Single JSON report payload for both domains, with room for future assays.
- First‑page executive summary; deep variant & biomarker detail; QC/methods; sign‑out & versioning.
- Interop: FHIR DiagnosticReport/Observations + Conditions/Procedures; GA4GH VRS shells.
- Diagnostic/procedure code compatibility: ICD‑10‑CM, SNOMED CT, CPT, HCPCS, ICD‑10‑PCS, and VA VUID.
- Patient‑facing summarization layer for plain‑language reports.

## 2) Goals & Non‑Goals (updated)
**Goals**
- Deliver a **robust, production‑grade scaffold** that can **scale across many different customers** (multi‑tenant‑aware config, theming, feature flags).
- Emphasize **reproducibility** and **end‑game portability** (stable schemas, deterministic rendering, transportable artifacts), while **shipping a working end‑to‑end test case first**.
- Preserve raw fidelity (canonical JSON payloads) with normalized views for search/analytics.
- Align to standards (FHIR Genomics, GA4GH VRS) and compliance (sign‑out, immutable payload hash, audit trails).
- Provide **clean integration seams** for the **health_portal dashboard (frontend)** and the **genomics_stack (backend)**.

**Non‑Goals (v0.1.x)**
- Building the full **portal shell or dashboard UX** — planned separately; this engine integrates with them.
- Full trial matcher and full PGx inference (deferred per roadmap).

## 3) Personas & User Journeys
- Molecular Pathologist/Director, Medical Oncologist/Geneticist, Genetic Counselor, **Practitioners** (MD/DO, DNP, RN, CNA, Nutritionists, PTs, Personal Trainers), Researchers, Patient Education, Patient.
- Primary flow: pipeline emits JSON → validation → persist → render → export → sign‑out → (optional) reissue.

## 4) System Overview
Ingress adapters → Validation & Mapping → Storage (JSONB + normalized) → Rendering (clinician/patient) → Export (FHIR/VRS) → Audit & Sign‑Out → Ops & Observability.

## 5) Data Model (Logical)
Top‑level Report: subject, specimen, indication, summary, **diagnoses[]**, **procedures[]**, findings (variants, biomarkers, phenotype, secondary findings), clinicalTrials[], recommendations[], methodsAndQC, fhir, signOut.

## 6) Evidence Model & Code Systems
- Classification supports AMP/ASCO/CAP tiers, ESMO ESCAT levels, ACMG/ClinVar.
- Evidence items include guideline, statement, disease, drugs, citations, level.
- Code systems: ICD‑10‑CM/SNOMED (diagnoses), CPT/HCPCS/ICD‑10‑PCS (procedures), VA VUID optional.

## 7) Storage Schema (Relational Expectations)
Tables: report, variant, biomarker; view: report_exec_summary. Versioning policy + immutable payload hash.

## 8) Interfaces & APIs (Internal)
Ingress (JSON intake + validate), Rendering (clinician HTML; patient mode later), Export (FHIR DR/Obs/Cond/Proc; VRS shells), Audit (sign‑out/lock).

## 9) UX & Report Layout (Clinician‑First)
Executive Summary (cards: actionability, biomarkers, therapies, trials) → Detailed Findings → QC/Methods → Signatures.

## 9.1) Clinical/Technical → Patient‑Facing Summarization
Reading level, selection rules (hide VUS by default), glossary/links, safety disclaimers, localization hooks, dual outputs (clinician & patient).

## 10) Non‑Functional Requirements
Security/compliance (HIPAA‑aligned logging; PHI scrubbing; least privilege), performance, reliability, observability.

## 11) Environments & Deployment Expectations
Local → Staging → Prod; patch‑style releases with install/verify scripts.

## 12) Dependency Matrix
Runtime: Python ≥3.11, Postgres ≥14. Optional: jsonschema, Jinja2/WeasyPrint/ReportLab, FHIR libs, VRS normalizer.

## 13) Implementation Plan (Milestones & WBS)
Milestone A (foundation, incl. integration stubs), Milestone B (interop/UX), Milestone C (matching/intelligence).

## 14) Definition of Done
Schemas frozen; migrations applied; renderer deterministic; FHIR bundle validates; security review; docs/runbooks ready.

## 15) Test Strategy
Schema tests, golden renders, DB migrations, export validation, performance tests.

## 16) Risk Register & Mitigations
Scope creep, terminology drift, evidence conflicts, PDF fidelity, data privacy.

## 17) Rollout & Change Management
Dev→Staging sign‑off→Prod; reissue policy; backups and restore drills.

## 18) Operational Runbooks (Initial)
Import failure triage; renderer fallbacks; export retries; reissue workflow.

## 19) Open Questions
FHIR target (R4B vs R5), PDF pipeline choice, concept‑mapping timing, payer integrations.

## 20) Acceptance Checklist (updated)
- [ ] Schemas versioned and frozen for v0.1.x
- [ ] Example payloads validated
- [ ] DB migration dry‑run on staging
- [ ] Renderer snapshot/print checks pass
- [ ] FHIR bundle validates
- [ ] Security review complete (hash/sign‑out/roles)
- [ ] **Integration validated:** health_portal dashboard renders; genomics_stack ingests
- [ ] Runbooks & release notes published

## 21) Integration — health_portal Frontend & genomics_stack Backend
**Frontend contracts**: `GET /reports/:id/summary`, `GET /reports/:id`, `GET /reports/:id/patient`, `GET /reports/:id/download?mode=clinician|patient`.
**Backend**: ingress adapter (emit canonical JSON), apply migrations, provenance in methodsAndQC, optional webhooks to portal.
**Separation of concerns**: portal/dashboard developed separately; this engine exposes stable APIs/payloads for clean integration.
