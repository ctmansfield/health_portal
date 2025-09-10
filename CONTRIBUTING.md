# CONTRIBUTING

This repo supports **parallel development** across DB, Application Layer, and Dashboard. All contributors (humans + LLM coders) must follow these rules:

## Golden Rules
1) **Do not cross boundaries.** Dashboard never touches DB. App layer is the only DB client.
2) **Contracts first.** Any change to DB schema, API, or payloads must start by bumping versions in `core/contracts.yaml` (SEMVER).
3) **OpenAPI is the source of truth** for dashboard data shapes.
4) **CI must pass** `VERIFY_ALL.sh` checks before merge.

## LLM Coder Quickstart
Use this prompt when working in this repo:

> You are coding for the `health_portal` project. Respect component boundaries: Dashboard ↔ API ↔ DB. Do not modify `services/healthdb-pg-0001/migrations` unless the task is DB-*. Do not change `api/openapi.*.yaml` unless the task is APP-*. For UI tasks, only touch frontend code. Any contract change requires updating `core/contracts.yaml` and corresponding tests. Run `./VERIFY_ALL.sh` locally and ensure it passes.

### Common Tasks
- **DB-***: add migrations under `services/healthdb-pg-0001/migrations/`; update `core/contracts.yaml` (db_schema_version MINOR).
- **APP-***: extend handlers; update `api/openapi.genomics_reports.v1.yaml` (MINOR for additive fields); update `core/contracts.yaml` (api_version if needed).
- **UI-***: consume API only; regenerate client if used; no DB access.

## PR Checklist
- [ ] References Issue ID(s) (DB-*, APP-*, UI-*)
- [ ] Updated `core/contracts.yaml` if any contract changed
- [ ] Updated/OpenAPI and/or migrations if applicable
- [ ] Ran `./VERIFY_ALL.sh` locally (paste tail)
- [ ] Added/updated tests & snapshots

## Getting Started
- `./VERIFY_ALL.sh` — runs schema presence checks, OpenAPI sanity, and sample render (if installed).
- See `docs/reporting_scaffold/` for architecture and design.
