# Change Log

## [Unreleased]

### Added
- New shared labs UI (`labs_shared_v2.js`) with grouped clinical categories and selectable metrics.
- Backend `/labs/{person_id}/labs-metadata` API endpoint for lab metrics metadata grouped by clinical category.
- Backend `/labs/{person_id}/all-series` API endpoint consolidating all lab metric series from `analytics.mv_labs_all` view.
- Template `labs_shared_page.html` for shared labs UI with required JS includes and Chart.js with date adapter.
- Basic `labs_critical_page.html` template for critical labs UI.
- `dashboard_events.js` client script for dynamic loading and rendering of recent events table on `/dashboard/events` page.
- Added medication overlay support with configurable test events on critical, liver, and shared labs pages.
- Toggle controls on labs pages to show/hide medication overlays.

### Fixed
- Indentation and syntax errors in `srv/api/dashboard.py` routes causing server start failures.
- Removed missing `dashboard_events.js` JS file reference from events.html previously causing 404 errors.
- Fixed chart rendering errors by adding Chart.js date adapter (`chartjs-adapter-date-fns`).
- Excluded vital sign metrics (hr, spo2) from shared labs metric metadata listing both server-side and client-side.
- Fixed local variable scoping issues in exception handlers in dashboard.py routes.
- Added detailed traceback logging in exception handlers to aid debugging.
- Ensured static asset and router inclusion order correctness in `srv/api/main.py` and templates.

### Removed
- Removed hardcoded or duplicate banner markup causing UI duplication.
- Removed redundant or broken JS includes causing 404 errors.

### Testing
- Adjusted event page and other UI integration tests to reflect current static content and component presence.

---

Please review and adjust for accuracy or completeness as needed.
