# PROMPT for LLM Coder — DB-1 (Baseline schema & views (report, variant, biomarker; report_exec_summary))

You are coding for the `health_portal` project using the Coding Blocks system.

## Boundaries
- Component: db — only touch the paths listed below.
- Do **not** modify other components.
- For any contract change, update `core/contracts.yaml` (and related artifacts) explicitly.

## Paths Allowed
- services/healthdb-pg-0001/migrations/
- app/reporting_scaffold/schemas/json/*

## Acceptance
- Migrations apply/rollback cleanly in staging
- View `report_exec_summary` returns expected columns

## Helpful Docs
- docs/reporting_scaffold/Program_System_Design_Consolidated_v0.1.x.md
- docs/reporting_scaffold/Parallel_Workstreams_and_Interface_Contracts.md
- docs/reporting_scaffold/System_Architecture_and_Design.md

## Steps
1) Read the docs above.
2) Implement the acceptance items.
3) Run any available local checks (VERIFY_ALL.sh if present).
4) Commit via `scripts/block/close_block.sh DB-1 "commit message"`.
