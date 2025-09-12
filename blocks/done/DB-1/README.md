# DB-1: DB-1

| Key | Value |
|---|---|
| **ID** | `DB-1` |
| **Component** | `n/a` |
| **Status** | `done` |
| **Weight** | 0 |
| **Assignee** | unassigned |
| **Dependencies** | — |

## Purpose & Scope
Create baseline analytics schema and views for reports (report, variant, biomarker) and `report_exec_summary`.


## Interfaces & Contracts
- - View: `analytics.report_exec_summary(id,title,result,signed_out_at)`
- - Tables: `analytics.report`, `analytics.variant`, `analytics.biomarker`


## Acceptance Criteria
- (none)


## Touch Points
- (none)


## Design Notes
- Follow ADRs for versioning and JSONB canonical forms.
- No PHI in logs. Enforce auth where applicable.
- Return stable, backward-compatible payloads.


## Run & Verify (local)
- psql -c "SELECT * FROM analytics.report_exec_summary LIMIT 5;"
- services/healthdb-pg-0001/migrations/verify_report_baseline.sh


## Suggested Branch & PR
- Branch: `db-1/feature`
- Create a small PR; include test results and screenshots for UI.


## Related Docs
- `docs/architecture/C4_System_Context.md`
- `docs/architecture/C4_Containers.md`
- `docs/architecture/ADRs/ADR-0001-FHIR_Target.md`
- `docs/reporting_scaffold/System_Architecture_and_Design.md`
- `docs/Blocks_Working_Agreement.md`
- `docs/LLM_Coder_VS_Quickstart.md`
