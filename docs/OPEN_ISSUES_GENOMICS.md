OPEN ISSUES & ROADMAP — Integrating Genomics Stack with Health Portal Dashboard

Overview
--------
Goal: reuse the Health Portal dashboard as a front-end for the genomics-stack to provide clinicians and analysts a unified UI for variant reports, VEP cache status, risk reports, and monitoring. The genomics-stack lives at /mnt/nas_storage/genomics-stack (separate repo). This document lays out a prioritized, actionable list of tasks (issues) required to integrate the two systems while keeping the projects independent and non-conflicting.

Principles
----------
- Non-destructive: the dashboard will only read data or call safe endpoints; no writes to genomics-stack sources unless explicitly approved.
- Reuse: use existing DB connections (HP_DSN) where genomics data resides, or read curated reports from the genomics repo reporting directories.
- Security: protect access with the same API key/session model used by the dashboard; plan for role-based access for clinicians.
- Incremental delivery: small, testable tasks with clear acceptance criteria.

How to use this file
--------------------
- Each task has an ID (GEN-xxx), a short description, rationale, acceptance criteria, estimate (S/M/L), and suggested files or places to change.
- Start at the top (high priority) and work down.

Priority roadmap (high → low)
------------------------------
GEN-001: Discover genomics data sources & schema (HIGH)
- Task: Inventory where genomics data lives and how to query it: DB connections (Postgres instances in docker_pg_stack), report directories (/mnt/nas_storage/genomics-stack/risk_reports/out), VEP cache location, guard scripts.
- Rationale: Without a canonical data map we cannot reliably build views or API endpoints.
- Acceptance:
  - A small YAML manifest file created at docs/genomics_data_manifest.yaml listing: DB host/port (or DSN env var), report directories, key tables, VEP cache paths, and any guard scripts.
  - Confirmed sample SQL SELECT statements that return sample records and counts.
- Estimate: S
- Suggested files: docs/genomics_data_manifest.yaml (new), docs/OPEN_ISSUES_GENOMICS.md (this file updated)

GEN-002: Add genomics section to dashboard nav and placeholder pages (HIGH)
- Task: Extend the dashboard UI with a left-side nav or top nav item “Genomics” and a placeholder page that explains integration status and links to reports.
- Rationale: Provide visible integration point without breaking current UI.
- Acceptance:
  - New route /genomics in srv/api/dashboard or a dedicated srv/api/genomics router returning a template.
  - Template shows links to: Reports, VEP Cache status, Recent Jobs.
- Estimate: S
- Files: srv/api/templates/genomics.html, srv/api/genomics.py, srv/api/main.py include router

GEN-003: Add API endpoints to serve genomics reports (HIGH)
- Task: Build read-only endpoints under /v1/genomics to list available reports and serve report metadata (and, optionally, the report file content if small or provide a link to file).
- Rationale: Allow the dashboard to request reports via API rather than directly reading file system (gives a single integration point and consistent auth).
- Acceptance:
  - GET /v1/genomics/reports?limit=... returns list of report metadata (patient_id, report_path, generated_at, summary fields).
  - GET /v1/genomics/reports/{report_id} returns metadata and a URL or ephemeral token to download the file.
- Estimate: M
- Files: srv/api/v1/genomics.py, app/hp_etl/genomics.py (small helper), tests/test_genomics_api.py

GEN-004: Create materialized views for genomics summary (MEDIUM)
- Task: Add SQL migrations to create views in the analytics schema to summarize variant counts, highest-risk reports, and daily report counts.
- Rationale: Fast queries for the dashboard; avoid scanning raw files each request.
- Acceptance:
  - New migration SQL (services/healthdb-pg-0001/init/05x_genomics_views.sql) creating e.g. analytics.mv_genomics_report_counts, analytics.mv_genomics_top_variants.
  - Indexes to support filters by person_id and date.
- Estimate: M

GEN-005: VEP cache & pipeline status endpoints (MEDIUM)
- Task: Expose VEP cache health and pipeline job statuses (via reading guard script outputs or status files produced by genomics-stack).
- Rationale: Clinicians/ops need to know if annotation infrastructure is ready.
- Acceptance:
  - GET /v1/genomics/vep/status returns JSON: {cache_present: bool, last_sync: iso, size_gb: float}
  - GET /v1/genomics/jobs returns recent pipeline job statuses (success/fail, time)
- Estimate: M
- Files: srv/api/v1/genomics.py additions, helper that reads file metadata

GEN-006: Report viewer: render risk report PDFs (or HTML) embedded (MEDIUM)
- Task: Provide UI in dashboard for viewing individual risk reports (render PDF in-browser or show HTML view). If PDF, serve via streaming response with proper content-type and inline disposition.
- Rationale: Clinicians should be able to open a report without leaving the dashboard.
- Acceptance:
  - Clicking a report in the dashboard opens a new route /genomics/reports/{id} that serves the report file inline.
  - Respect auth; prevent directory traversal.
- Estimate: M
- Files: srv/api/genomics.py, srv/api/templates/genomics_report.html

GEN-007: Variant table with filters, pagination and links to external databases (LOW)
- Task: Build a variant table UI: gene, HGVS, consequence, frequency, ClinVar/gnomAD links. Include filters by gene, consequence, and pagination.
- Rationale: Core functionality for clinical review of variants.
- Acceptance:
  - Endpoint /v1/genomics/variants?patient_id=... supports pagination; UI shows table with links.
- Estimate: L

GEN-008: Auth & RBAC for genomics (HIGH)
- Task: Plan and implement role-based access control for genomics features: clinicians vs ops vs researchers. Initially flag this as open issue; eventual implementation could be OAuth2/JWT or session roles.
- Rationale: Genomics data is sensitive and requires stricter access controls.
- Acceptance:
  - Design doc produced describing approach (session cookie vs JWT vs OAuth), migration steps, and required schema changes (users/roles table).
- Estimate: M-L
- Files: docs/genomics_auth_design.md (new)

GEN-009: Tests, CI & deployment (HIGH)
- Task: Add tests for the new genomics API and views, and add a CI workflow that runs pytest and lints. Also document deployment steps for adding migrations to the DB.
- Rationale: Ensure reliability and regression safety.
- Acceptance:
  - tests/test_genomics_api.py exists and runs under pytest without network (uses monkeypatch to stub file/DB access).
  - CI yaml added or documented steps to run tests locally.
- Estimate: M

GEN-010: UX polish & clinician feedback loop (ONGOING)
- Task: After initial integrations, schedule sessions with clinicians to collect feedback, then iterate on the UI (explainability of risk scores, drilldowns, export options).
- Rationale: Deliver a UI that is actually useful in clinical workflows.
- Acceptance:
  - A short report with prioritized feedback and at least 3 UI iterations planned.
- Estimate: ongoing

Technical approach notes
-------------------------
- Data access: two main patterns:
  1. Database-first: if genomics-stack writes structured tables into a Postgres instance, create SQL views and API endpoints that query those tables.
  2. Reports-first: if genomics-stack primarily emits files (risk_reports/out), build a small service that indexes report files into a DB table (reports index) and use that as a source-of-truth for API endpoints.

- Authentication: reuse HP_API_KEY for early iterations but track GEN-008 to implement stronger auth before production use.

- Performance: materialized views for expensive aggregations, refresh nightly or on demand with locking (reuse existing cron locking mechanism).

Next actions (immediate)
------------------------
1. Create docs/genomics_data_manifest.yaml (GEN-001).
2. Scaffold srv/api/v1/genomics.py with endpoints list and stub responses (GEN-003).
3. Add migration file skeleton for genomics views (services/healthdb-pg-0001/init/043_genomics_views.sql) — include placeholders (GEN-004).
4. Add tests/test_genomics_api.py with monkeypatch fixtures (GEN-009).

If you approve, I will generate these scaffold files and add them to the repo as a next patch.
