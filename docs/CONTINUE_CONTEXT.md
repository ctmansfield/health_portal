# Health Portal — LLM Coder Context (Continue)

## Repo Roots
- Incoming (ops apply): /mnt/nas_share/incoming
- Repo: /mnt/nas_storage/repos/health_portal
- Service (DB): /mnt/nas_storage/repos/health_portal/services/healthdb-pg-0001
- Local DB storage (bind-mount): /mnt/llmstore/health_portal/pgdata

## Schemas (already provisioned)
- fhir_raw.resources(resource_type, resource_id, resource jsonb, imported_at)
- analytics.data_events(… time-aligned event fields …)
- analytics.etl_state(key, value)
- analytics.person(person_id, tz)

## Coding Standards
- Python 3.12, no external network calls.
- Keep jobs idempotent; use analytics.etl_state for watermarks.
- Always store UTC; keep tz/local info in meta JSON.
- Don’t change files under services/healthdb-pg-0001 unless explicitly asked.
- Prefer small, composable CLIs over monoliths.

## Conventions
- Package: app/hp_etl
- CLI jobs: jobs/*.py (import hp_etl)
- Shell wrappers go in scripts/
- Make targets drive common tasks

## Acceptance Checks
- Run under: cd services/healthdb-pg-0001 && ./scripts/psql.sh
- SQL verify snippets provided in each task.
