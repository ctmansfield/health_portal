# Parallel Workstreams & Interface Contracts — v0.1.3

**Objective:** Allow **DB**, **Application Layer**, and **Dashboard** teams to code **in parallel** with **no overlap** by freezing **interfaces** and publishing a **Contracts Registry**.

---

## 0) Ground Rules
- **Single Source of Truth:** `core/contracts.yaml` stores versions for DB schema, API, and payload schemas.
- **No cross-layer reach:** Dashboard never touches DB; it consumes the API. App layer is the only writer to DB.
- **Change control:** Any contract change starts with a PR updating `core/contracts.yaml` (minor/major bump), then cascades to components.
- **Semantic Versioning:** PATCH (docs), MINOR (additive), MAJOR (breaking).

---

## 1) Component Boundaries & Dependencies
### DB (services/healthdb-pg-0001)
**Provides:** normalized tables, JSONB payload store, views.
**Depends on:** none at runtime; accepts migrations from App layer when bumped.
**Stable Contract:** `db_schema_version=1.0.0` (see contracts).
**Exports:** schema/migrations; view names; minimal seed fixtures for tests.

### Application Layer (app/ + srv/)
**Provides:** REST API (**read-only v1**) for reports; renderer; FHIR/VRS exporters; sign-out & hashing.
**Depends on:** DB schema `^1.0.0`; payload schemas `^1.0.0`.
**Stable Contract:** `api_version=1.0.0` + OpenAPI file; payload schema versions pinned in contracts.

### Dashboard (frontend)
**Provides:** clinician summary cards, full report view, patient-mode view.
**Depends on:** API `^1.0.0` only (no DB access).
**Stable Contract:** consumes OpenAPI 1.0; respects version header `Accept-Version` to negotiate minor changes.

---

## 2) RACI (Ownership)
- **Contracts Registry** — *Core Eng (R)*; Clinical/QA/Compliance (A/C); All teams (I)
- **DB Migrations** — *DB Team (R)*; App (C); Core Eng (A); Dashboard (I)
- **API** — *App Team (R)*; Core Eng (A); DB (C for performance); Dashboard (C)
- **Dashboard UI** — *Dashboard Team (R)*; App (C); Core Eng (A)

---

## 3) Feature Backlog by Component (parallelizable)
### 3.1 DB (Epic: Reporting Storage v1)
- **DB-1** Baseline schema & views aligned to report/codes schemas (status: ready). *Depends on:* contracts.yaml v1
- **DB-2** History & reissue policy tables (append-only; prior hash retention)
- **DB-3** Indexing strategy (GIN on JSONB keys for findings.variants.geneSymbol; coverage on signOut.date)
- **DB-4** Analytics views (variant frequency by gene; biomarkers distribution) — read-only
- **DB-5** Migration harness & rollback scripts (Makefile targets)
> **Interfaces touched:** db_schema_version (bump MINOR for additive columns/views)

### 3.2 Application Layer (Epic: Reports API v1)
- **APP-1** Ingest endpoint/service for canonical JSON (internal job) + schema validation
- **APP-2** `/reports/{id}` (clinician payload) — OpenAPI v1
- **APP-3** `/reports/{id}/summary` (dashboard card payload)
- **APP-4** `/reports/{id}/patient` (patient-mode HTML/JSON)
- **APP-5** Sign-out flow — versioning & payload hash
- **APP-6** FHIR export stub (DR/Obs/Cond/Proc) and VRS shell export
- **APP-7** Renderer stabilization & snapshot tests
> **Interfaces touched:** API (openapi.yaml) MINOR for additive fields; payload schemas pinned via contracts.yaml

### 3.3 Dashboard (Epic: Report Surfaces v1)
- **UI-1** Summary card (banner, key findings, biomarkers, trials count)
- **UI-2** Full clinician report view (server-rendered HTML or client render from JSON)
- **UI-3** Patient-mode view & download
- **UI-4** Feature flags & theming tokens per customer
- **UI-5** Routing, error states, and loading skeletons
> **Interfaces touched:** consumes API; break glass only if API version bumps MAJOR

---

## 4) Immutable Interfaces (v1.0.0)
- **DB → App**: tables `report`, `variant`, `biomarker`; views: `report_exec_summary` (columns: id,title,result,signed_out_at). No breaking changes without MAJOR.
- **App → Dashboard**: OpenAPI 1.0 endpoints above; response shapes tied to payload schemas (pinned).

---

## 5) Version Bump Policy & Workflow
1. Open PR changing `core/contracts.yaml` with rationale (MINOR/MAJOR).
2. Update affected artifacts (migrations, schemas, openapi).
3. CI runs: schema tests, openapi lint, golden renders.
4. Tag release and broadcast.
5. Dashboard pulls updated OpenAPI and regenerates client (if used).

---

## 6) Milestone Slice (2-week parallel plan)
- **Week 1**
  - DB-1, DB-3; APP-2, APP-3; UI-1, UI-5
- **Week 2**
  - DB-2, DB-5; APP-4, APP-5; UI-2, UI-3, UI-4
- **Exit criteria:** all v1 endpoints live, snapshot tests pass, dashboard renders summary & full view from real sample

---

## 7) Non-Overlap Rules
- Only **DB team** edits `services/healthdb-pg-0001/migrations`; app submits requests via issues/PRs.
- Only **App team** edits `api/openapi.*.yaml` and server handlers; dashboards never patch API behavior directly.
- Only **Dashboard team** edits UI; any data shape change must be reflected in OpenAPI first.

---

## 8) Backward Compatibility Guarantees
- Additive DB columns and API fields are **non-breaking**.
- Deprecated fields remain at least one MINOR series with warnings in responses.
- Patient-mode HTML stable for printer templates across MINOR series.

---

## 9) Acceptance (for this plan)
- Contracts registry present and versioned.
- OpenAPI file published and linked in docs.
- Work items labeled in Issues matching IDs here (DB-*, APP-*, UI-*).
