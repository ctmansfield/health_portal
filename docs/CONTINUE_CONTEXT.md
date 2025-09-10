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

## Pre-commit Style & Linting

To install and enable code formatting & hygiene checks, run:

```bash
pip install pre-commit black
pre-commit install
```

Optionally check all files:

```bash
pre-commit run --all-files
```

This will enforce: trailing whitespace, YAML validity, consistent line endings, and code formatting (Black, line length 100).

## Acceptance Checks
- Run under: cd services/healthdb-pg-0001 && ./scripts/psql.sh
- SQL verify snippets provided in each task.

## Open Issues / TODO
- AUTH-HARDENING: Dashboard currently uses API key via HP_API_KEY and an httpOnly cookie for convenience. This is flagged for future hardening: consider replacing with short-lived session tokens, CSRF protection, secure cookie flags in HTTPS, and role-based authorization. See srv/api/auth.py and srv/api/README-dashboard.md.

Recent work (dashboard & views)
- Added an enhanced dashboard with HR and SpO2 charts, a Findings table, and a Genomics integration UI. See srv/api/templates and srv/api/genomics.py.
- Added a drilldown page for recent events: GET /dashboard/events (template: srv/api/templates/events.html).
- Added jobs/refresh_materialized_views.py and a cron entry (03:00) to refresh materialized views nightly (uses flock /tmp/hp_refresh_views.lock).
- Added jobs/index_genomics_reports.py and analytics.genomics_reports migration to index genomics reports (separate integration branch).

Operational notes
- Run `bash scripts/cron/install_cron.sh` to update crontab and include nightly refresh + indexing jobs.
- The refresh job will attempt CONCURRENTLY refresh and fall back to non-concurrent if needed. Large materialized views may lock; consider scheduling window or using CONCURRENTLY where supported.
