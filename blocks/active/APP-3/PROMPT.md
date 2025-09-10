# PROMPT for LLM Coder — APP-3 (GET /reports/{id}/summary — dashboard card)

You are coding for the `health_portal` project using the **Coding Blocks** system.

## Boundaries
- Component: app — only touch the paths listed below.
- Do **not** modify other components.
- For any contract change, update `core/contracts.yaml` (and related artifacts) explicitly.

## Paths Allowed
- srv/ or app/


## Acceptance
- Returns banner, key findings, biomarkers, trials count
- Cache by report id + version (optional)


## Helpful Docs
- api/openapi.genomics_reports.v1.yaml


## Steps
1) Read the docs above.
2) Implement the acceptance items.
3) Run any available local checks (VERIFY_ALL.sh if present).
4) Commit via `scripts/block/close_block.sh APP-3 "commit message"`.
