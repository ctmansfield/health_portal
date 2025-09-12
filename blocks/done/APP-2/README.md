# APP-2: APP-2

| Key | Value |
|---|---|
| **ID** | `APP-2` |
| **Component** | `n/a` |
| **Status** | `done` |
| **Weight** | 0 |
| **Assignee** | unassigned |
| **Dependencies** | — |

## Purpose & Scope
Expose clinician payload endpoint.


## Interfaces & Contracts
- - **GET /reports/{id}** → returns canonical JSON stored in `analytics.report.payload`.
- - OpenAPI: `api/openapi.genomics_reports.v1.yaml`


## Acceptance Criteria
- (none)


## Touch Points
- (none)


## Design Notes
- Follow ADRs for versioning and JSONB canonical forms.
- No PHI in logs. Enforce auth where applicable.
- Return stable, backward-compatible payloads.


## Run & Verify (local)
- pytest -q tests/test_app_reports.py::test_get_report_payload


## Suggested Branch & PR
- Branch: `app-2/feature`
- Create a small PR; include test results and screenshots for UI.


## Related Docs
- `docs/architecture/C4_System_Context.md`
- `docs/architecture/C4_Containers.md`
- `docs/architecture/ADRs/ADR-0001-FHIR_Target.md`
- `docs/reporting_scaffold/System_Architecture_and_Design.md`
- `docs/Blocks_Working_Agreement.md`
- `docs/LLM_Coder_VS_Quickstart.md`
