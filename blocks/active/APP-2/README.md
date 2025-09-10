# APP-2 — GET /reports/{id} — full clinician payload

**Component:** app
**Status:** active
**Assignee:** Bob
**Opened:** 2025-09-10T22:00:48.863776Z

## Context & Links
- api/openapi.genomics_reports.v1.yaml


## Paths You May Touch (stay in your lane)
- srv/ or app/ (API handlers)


## Acceptance Criteria
- [ ] OpenAPI contract tests pass
- [ ] Example payload returns; renderer dev route can display


## Notes
- Respect the Contracts Registry (core/contracts.yaml) for version bumps.
- Do not cross boundaries (DB vs App vs UI). Use the API for UI work.
