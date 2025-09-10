# APP-3 — GET /reports/{id}/summary — dashboard card

**Component:** app
**Status:** active
**Assignee:** Carol
**Opened:** 2025-09-10T22:00:50.092763Z

## Context & Links
- api/openapi.genomics_reports.v1.yaml


## Paths You May Touch (stay in your lane)
- srv/ or app/


## Acceptance Criteria
- [ ] Returns banner, key findings, biomarkers, trials count
- [ ] Cache by report id + version (optional)


## Notes
- Respect the Contracts Registry (core/contracts.yaml) for version bumps.
- Do not cross boundaries (DB vs App vs UI). Use the API for UI work.
