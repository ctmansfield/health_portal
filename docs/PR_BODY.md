Title: feat(ui+api): Summary Card, Labs Critical page, APP-9 critical-series + Redis caching + preview tooling

Summary

This PR delivers a lightweight, accessible Summary Card component and a new Labs Critical UI page that consumes the APP-9 API (GET /labs/{person_id}/critical-series). It implements daily and hourly aggregation, timezone-aware timestamps (UTC + person-local), ETL-aware server-side caching (Redis preferred), preview tooling for designers, export CSV, and integration tests including a Docker-based Postgres integration.

Key highlights
- UI
  - app/templates/components/report_summary_card.html — Summary Card partial
  - app/static/js/report_summary_card.js — Summary Card client behavior
  - app/templates/components/labs_critical_page.html — Labs Critical page (charts container + toolbar)
  - app/static/js/labs_critical_v2.js — Labs client script (charts, export, preview toggle, persistent preference scope)
  - Dashboard integration: link to labs page added to dashboard template

- API
  - srv/api/reports.py
    - GET /labs/{person_id}/critical-series
      - supports metrics aliases (hr, spo2) and agg=daily|hourly
      - hourly resampling from analytics.data_events; daily from analytics.mv_daily_vitals
      - returns UTC and person-local timestamps (t_utc, t_local) and tz metadata
      - ETL-aware caching: checks analytics.etl_state for mv_daily_vitals_version and critical_series_ttl
      - supports lab metric lookup (analytics.lab_results) for additional metrics when present

- Cache
  - app/hp_etl/cache.py (new): Redis-backed cache preferred (REDIS_URL), falls back to process-local simple_cache if Redis unavailable

- Tests
  - tests/test_ui_report_summary_card.py — UI shell assertions for Summary Card
  - tests/test_ui_labs_critical.py — UI shell test for Labs Critical page
  - tests/test_api_critical_series.py — unit tests for critical-series (monkeypatched DB)
  - tests/integration/test_api_critical_series_integration.py — Docker-based Postgres integration (opt-in via HP_DOCKER_TEST=1)
  - pytest.ini updated to register integration mark

- Docs
  - docs/UI_SUMMARY.md — high-level summary and how to run
  - docs/PR_CLOSURE.md — closeout notes
  - docs/PR_BODY.md (this file) — copy-paste PR body

How to run & verify locally

1) Optional: run Redis for cache (recommended for parity with production):
   docker run -d --name hp-redis -p 6379:6379 redis:7
   export REDIS_URL=redis://localhost:6379/0

2) Run unit tests:
   . .venv/bin/activate
   pytest -q

3) Run integration test (starts a temporary Postgres container when HP_DOCKER_TEST=1):
   export HP_DOCKER_TEST=1
   pytest -q tests/integration/test_api_critical_series_integration.py

4) Run the app and view pages:
   . .venv/bin/activate
   uvicorn srv.api.main:app --reload

   Pages:
   - Summary card preview: /ui/reports/<id>/summary-card
   - Labs page (designer preview): /ui/people/<id>/labs/critical?preview=1
   - Dashboard: /dashboard (link to labs charts in Summary)

Design & accessibility notes
- Charts are rendered inside <figure> with <figcaption> for semantic clarity
- Canvas elements include aria-label and role="img"
- Dynamic updates use aria-live="polite"
- Export action provides CSV download for each metric
- Toolbar includes an accessible toggle and a scope selector (This person / Global). Preferences persist in localStorage.

Operational notes
- Caching: the app will prefer Redis if REDIS_URL points to a reachable redis instance. If not present, it falls back to the in-process cache (simple_cache). For production scale, use Redis across workers.
- ETL invalidation: the cache key includes analytics.etl_state.mv_daily_vitals_version when present. Set the key in ETL to invalidate caches after refresh.

Files changed (high level)
- Added: app/templates/components/report_summary_card.html
- Added: app/static/js/report_summary_card.js
- Added: app/templates/components/labs_critical_page.html
- Added: app/static/js/labs_critical_v2.js
- Added: app/hp_etl/cache.py
- Modified: srv/api/reports.py (critical-series + caching + hourly aggregation + lab lookups)
- Modified: srv/api/dashboard.py (UI routes + preview endpoint)
- Modified: srv/api/templates/dashboard.html (link)
- Tests added/updated: tests/*
- Docs added: docs/UI_SUMMARY.md, docs/PR_CLOSURE.md, docs/PR_BODY.md

Suggested branch & PR title
- Branch: feat/ui-labs-critical-and-caching
- PR title: feat(ui+api): labs critical page, APP-9 critical-series, Redis caching, preview tooling

Suggested PR body (copy/paste from top of this file)

Review notes / requested reviewers
- UI: please review component markup and styling (app/templates/components/*, style.css)
- Backend: please review SQL, timezone handling, and caching logic (srv/api/reports.py)
- Ops: please verify Redis setup and ETL invalidation readiness (analytics.etl_state keys)

If you want, I can:
- Open the branch and prepare a Git push + PR body text ready to paste into your repo host (tell me the remote/branch to push), or
- Make Redis mandatory and fail-fast if not available (not recommended for local dev), or
- Replace the preview endpoint with multiple sample datasets selectable by query param

-- End of PR body
