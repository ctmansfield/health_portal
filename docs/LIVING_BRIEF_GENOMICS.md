LIVING BRIEF — Genomics Integration (Health Portal)
===============================================

Purpose
-------
This living brief captures the current plan and artifacts for integrating the genomics-stack into the Health Portal dashboard. It is intentionally concise and descriptive so any engineer can pick up where we left off.

Location of artifacts
---------------------
- Detailed roadmap and open issues: docs/OPEN_ISSUES_GENOMICS.md
- Discovery manifest (data sources): docs/genomics_data_manifest.yaml
- Auth design (GEN-008): docs/genomics_auth_design.md
- SQL migration to index reports: services/healthdb-pg-0001/init/044_genomics_reports.sql
- Job to index report files: jobs/index_genomics_reports.py
- API scaffolds (v1): srv/api/v1/genomics.py
- UI scaffolds: srv/api/genomics.py, srv/api/templates/genomics.html, srv/api/templates/genomics_report.html
- Tests: tests/test_genomics_api.py, tests/test_genomics_ui.py

Current status
--------------
- Scaffolding and initial migrations created and checked into repo.
- Indexing job implemented and unit-tested (file-system discovery is heuristical at present).
- Dashboard endpoints and UI pages implemented to read from analytics.genomics_reports.
- Auth hardening (GEN-008) remains a prioritized open issue and is documented in docs/genomics_auth_design.md.

Next immediate actions
----------------------
1. Apply SQL migrations to the target database.
2. Run the indexing job once to populate analytics.genomics_reports and verify content.
3. Add the indexing job to nightly cron with flock locking (scripts/cron/install_cron.sh pattern).
4. Implement report download streaming (already implemented) and add file-type checks; ensure path safety.
5. Add pagination and filters to the UI for large report sets.
6. Implement GEN-004 (materialized genomics summary views) for dashboard performance.
7. Implement GEN-008 (Auth & RBAC) to secure sensitive genomics data.

Longer-term
-----------
- Add a reports-indexing pipeline that extracts structured metadata from reports (patient, study, summary JSON) to populate analytics.genomics_reports.summary JSONB (improves searchability).
- Implement role-based UI behavior (clinician vs ops vs research) once GEN-008 is implemented.
- Add SSO/OIDC integration if required by operations/enterprise policy.

How to contribute
-----------------
- When working on a genomics task, follow the repository discipline: implement changes as small patches, include an install.sh / verify.sh if relevant, and update this living brief on completion.
- For any cross-project impacts (networking, LLM infra, ops), update the corresponding living briefs listed in the session contexts.

Open issues (high priority)
---------------------------
- GEN-008: Auth hardening and RBAC (see docs/genomics_auth_design.md) — do not expose genomics data to unauthenticated users in production.
- GEN-004: Create materialized summary views for genomics to accelerate dashboard queries.

Contacts
--------
- Chad (repo owner / platform)
- Ops team — for DB migration & deployment support

Revision history
----------------
- 2025-09-09: Created; captured roadmap, migration and scaffolding files.
