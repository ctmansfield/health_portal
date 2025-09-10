# DB-1 — Baseline schema & views (report, variant, biomarker; report_exec_summary)

**Component:** db
**Status:** active
**Assignee:** Alice
**Opened:** 2025-09-10T22:16:00.026827Z

## Context & Links
- docs/reporting_scaffold/Program_System_Design_Consolidated_v0.1.x.md
- docs/reporting_scaffold/Parallel_Workstreams_and_Interface_Contracts.md
- docs/reporting_scaffold/System_Architecture_and_Design.md

## Paths You May Touch (stay in your lane)
- services/healthdb-pg-0001/migrations/
- app/reporting_scaffold/schemas/json/*

## Acceptance Criteria
- [ ] Migrations apply/rollback cleanly in staging
- [ ] View `report_exec_summary` returns expected columns

## Notes
- Respect the Contracts Registry (core/contracts.yaml) for version bumps.
- Do not cross boundaries (DB vs App vs UI). Use the API for UI work.
