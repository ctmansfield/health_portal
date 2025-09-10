OUTSTANDING TASKS & DEVELOPMENT BACKLOG

This file aggregates active open issues and remaining development work across the Health Portal repo. Use it as a single-source checklist when planning sprints or handoffs.

Top priority
------------
- AUTH-HARDENING (GEN-008)
  - Implement server-side sessions, users/roles, RBAC, and CSRF protections.
  - Files: services/healthdb-pg-0001/init/045_auth.sql, srv/api/auth_user.py, scripts/create_user.py
  - Status: migration added; auth_user scaffolded; passlib required; tests pending.
  - Estimate: 3–6 days.

High priority (ops & reliability)
---------------------------------
- Nightly materialized view refresh and cron
  - Ensure jobs/refresh_materialized_views.py runs via cron with flock; already added in scripts/cron/install_cron.sh
  - Verify refresh success regularly and tune concurrency.
  - Status: installed in crontab when requested; manual refresh tested.
  - Estimate: 0.5 day to finalize logging/alerts.

- Genomics indexing cron
  - Ensure jobs/index_genomics_reports.py runs nightly to populate analytics.genomics_reports.
  - Status: job present; migration created; table empty until files/indexing run.
  - Estimate: 0.25 day to wire cron and verify.

Medium priority (features)
--------------------------
- Promote in-process cache to Redis for multi-worker deployments
  - Implement REDIS_URL-backed cache in app/hp_etl/simple_cache.py with fallback to in-process cache.
  - Status: in-process cache implemented; Redis support pending.
  - Estimate: 1 day.

- Events pagination and CSV/NDJSON export
  - Add server-side pagination and an export endpoint; add UI Export button.
  - Status: events JSON endpoint and client exist; pagination + export pending.
  - Estimate: 0.75 day.

- Chart drilldown (click on a day point → open events for that day)
  - Add click handlers on hrChart to open /dashboard/events filtered for the clicked day & metric.
  - Status: planned; UI scaffolds ready.
  - Estimate: 0.5 day.

Low/ongoing
-----------
- CI: pytest + lint GitHub Actions
  - Add workflow to run tests and black/pre-commit on push/PR.
  - Status: tests present locally; CI config pending.
  - Estimate: 0.5–1 day.

- UI polish & accessibility
  - Improve color contrast, responsive design, keyboard navigation, and ARIA attributes for dashboards and tables.
  - Status: basic responsive layout added; further polish pending.
  - Estimate: 1–2 days incremental.

Testing & docs
--------------
- Unit and integration tests
  - Increase coverage around auth, events export, indexing job, and API endpoints.
  - Document runbooks and add verify.sh for new migrations.

- Living briefs and runbooks
  - The genomics living brief and open issues are present (docs/LIVING_BRIEF_GENOMICS.md, docs/OPEN_ISSUES_GENOMICS.md). Ensure they are updated with progress and operations steps after each change.

How to use
----------
- Pick the highest-priority item and run small incremental patches (one feature or migration per patch).
- Add tests and docs alongside each change.
- Use the existing cron & lock pattern (flock) for scheduled jobs.

If you want, I can start implementing AUTH-HARDENING immediately (create missing tests, finalize migrations, implement session cleanup jobs, and create the create_user CLI). Say “start AUTH” and I’ll begin producing patches and tests.
