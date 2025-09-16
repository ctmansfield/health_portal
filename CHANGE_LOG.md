# Change Log

## Shared Labs Feature Improvements

- Implemented a new client-side module (`labs_shared_v3.js`) that:
  - Displays a comprehensive catalog of lab metrics merged from person metadata and a global metrics catalog.
  - Supports disabled controls for lab metrics without available data.
  - Uses a two-column grouped layout with Select all / Clear buttons.
  - Implements multi-axis Chart.js plotting with unit-aware labeling.
  - Provides debug summaries and medication event notifications.
  - Excludes vital metrics (hr, spo2) from the labs shared UI.

- Updated the existing client (`labs_shared_v2.js`) to:
  - Prevent execution when `labs_shared_v3.js` is present to avoid duplicate initialization.
  - Filter out vitals from display and data.

- Updated the server API to:
  - Provide a merged lab metrics catalog combining metrics observed in person data and metrics from a local LOINC mapping CSV.
  - Exclude vitals (hr, spo2) from labs metadata and series responses.

- Changed shared labs page template to:
  - Include `labs_shared.js` first (for shared utilities).
  - Load `labs_shared_v3.js` next (primary client implementation).
  - Load `labs_shared_v2.js` last (fallback, no-op if v3 is present).

- Fixed script loading order in the shared labs page template to ensure dependencies are loaded before dependent scripts.

- Enhanced debug tooling with exposure of window variables and a debug API endpoint `/debug/labs` for server-side lab data checks.

- Improved error handling and user notifications for missing data or load failures.

- Overall achieve feature completeness, improved UX, and reliable chart rendering for the Shared Labs feature.

CHANGE LOG
==========

2025-09-13 - Created CHANGE_LOG.md to track repository fixes and investigations. (assistant)

2025-09-13 - Modified srv/api/main.py: removed duplicate /static mount and consolidated static directory path to use package directory (os.path.join). Reason: duplicate mounts and inconsistent static path could cause static files to be served incorrectly.

2025-09-13 - Reviewed JavaScript assets in srv/api/static/js including labs_critical_v2.js and labs_critical_v2.fixed.js. No automatic changes applied to JS files to avoid further regressions; labs_critical_v2.js remains present and has an init guard and render debounce.

2025-09-13 - Fixed dashboard template layout HTML in srv/api/templates/dashboard.html where some tags were broken and the summary card markup was malformed. The file was restructured to ensure the following expected classes are present for tests and client scripts: dashboard-main, dashboard-grid, chart-wrap, summary-card, and the sparkline canvas elements (hrSpark, spo2Spark).

Actions performed (what I can do next if you want):
- Add/restore chart.umd.min.js into srv/api/static/js (copy from srv/api/static/js.broken/) so templates that ensure the Chart library can load it.
- Replace the JS file labs_critical_v2.js with the cleaned labs_critical_v2.fixed.js after you confirm (I can perform the replacement).
- Run test suite (pytest) locally and fix remaining failing tests.
- Start/stop the dev server for live verification (note: I cannot run long-lived background processes here; I'll provide the exact commands).

Files read during investigation:
- srv/api/main.py
- srv/api/templates/labs_critical.html
- srv/api/static/js/labs_critical_v2.js
- srv/api/static/js/labs_critical_v2.fixed.js
- tests/test_ui_labs_critical.py
- srv/api/templates/dashboard.html

If you want me to apply any of the "next" actions above, tell me which and I will edit files and append to this CHANGE_LOG accordingly.
2025-09-13 - Fix: Reverted/cleaned up srv/api/main.py static mount duplication and ensured static path uses package directory. (edited by assistant)

2025-09-13 - Add: Created CHANGE_LOG.md and noted edits.

2025-09-13 - Perf: Changed labs chart rendering (srv/api/static/js/labs_critical_v2.js) to reuse existing Chart instances where possible instead of destroying and recreating all charts on every render. This reduces CPU, network thrash and improves UI smoothness. The renderCharts function now:
- maps existing charts by metricKey,
- reattaches existing canvas elements into new containers when present,
- updates datasets/labels in-place for reused charts,
- creates new Chart instances only for new metrics and destroys charts no longer present.
Notes: Added conservative logging to help verify reuse. (edited by assistant)

2025-09-13 - Perf: Added idle scheduling to labs chart rendering (srv/api/static/js/labs_critical_v2.js). New helper scheduleIdle uses requestIdleCallback (with a 250ms timeout) and falls back to setTimeout. Chart updates for reused charts are now scheduled via scheduleIdle to reduce requestAnimationFrame / main-thread jank. New chart creations still occur, but heavy update work yields to the browser when busy.

Files changed:
- srv/api/static/js/labs_critical_v2.js (renderCharts reuse, scheduleIdle deferral)

How to test (basic):
- Hard-refresh the labs page and observe console logs for "created chart for" and "reused chart for" messages.
- Switch aggregation (daily/hourly) and verify reuse messages appear and redundant fetches are suppressed.
- Run pytest -q to confirm tests still pass.

1. Conversation Overview

The discussion revolved around debugging, refactoring, and extending a health portal’s JavaScript and Python codebase related to rendering and managing lab graphs in a web UI. Initially, the conversation focused on identifying and fixing a syntax error caused by stray text in a critical JavaScript file (labs_critical_v2.js). Subsequently, the investigation shifted towards optimizing chart rendering for performance and stability, addressing UI bugs, and expanding functionality by creating a separate liver panel charts page to test rendering behavior with different datasets. User requested incremental, traceable changes with comprehensive testing before moving on.

2. Active Development

Fixed a critical syntax error in labs_critical_v2.js caused by non-JS trailing text. A minimal safe loader script was created to avoid crashing while the comprehensive fix was prepared.
Refactored renderCharts in labs_critical_v2.js to reuse Chart.js instances by updating chart data in place instead of destroying and recreating charts on every render, significantly improving UI smoothness and CPU usage.
Added concurrency and data loading guards (_hp_inflight_fetch, _hp_last_data_loaded, aggregation checks) in loadWithAgg to prevent redundant network fetches and excessive re-renders.
Deferred expensive chart updates to idle time via requestIdleCallback with a fallback, initially improving smoothness but ultimately exposing Chart.js resolver bugs.
Reverted idle deferral due to Chart.js errors (TypeError, recursion in option resolvers), settling on synchronous chart updates but keeping animation disabled (animation: false) for performance.
Extended the system by creating a new “Liver Panel” page:
Added HTML template (labs_liver_page.html) mirroring the critical labs page layout.
Wired a new API route in dashboard.py to serve the liver panel page (/ui/people/{id}/labs/liver).
Modified client JS to read liver-specific metrics from data-metrics attribute and pass them in fetch requests.
Updated UI index (ui_index.html) and existing labs page to add links for the liver and critical labs respectively.
Planned additional improvements to throttle pointer and wheel event handlers and implement dataset downsampling for large datasets, deferred until stabilization was confirmed.
3. Technical Stack

Backend: Python with FastAPI framework; Jinja2 templates for server-side HTML rendering.
Frontend: Plain JavaScript (vanilla), DOM manipulation, async data fetching (fetch API).
Visualization: Chart.js library for rendering line charts, extended with custom plugins (hp_ref_bands).
Storage & State: LocalStorage for UI state persistence (series visibility, band toggle, etc.).
Patterns:
Defensive JS programming to avoid null pointer errors.
Client-side caching of preview data with TTL and inflight promise tracking.
Progressive enhancement with retries and fallbacks in data loading.
UI interactivity using pointer events with dragging, zooming, and keyboard accessibility.
Graceful degradation by switching between preview and live modes.
Performance techniques:
Chart reuse and incremental updates.
Debounced rendering cycles.
Scheduling non-critical JS via requestIdleCallback.
4. File Operations

JavaScript

srv/api/static/js/labs_critical_v2.js (Modified extensively)
Fixed syntax error issue.
Added chart reuse logic (mapped and updated existing Chart instances).
Added load concurrency guards.
Implemented and then reverted idle deferral of chart updates due to Chart.js API quirks.
Extended fetchSeries to accept and forward a metrics parameter.
Adjusted loadWithAgg to read data-metrics from containers for flexible metric fetching.
Templates

app/templates/components/labs_critical_page.html (Existing)
Added a link to the new liver panel page.
Added a link to view vitals charts.
app/templates/components/labs_liver_page.html (Created new)
Cloned from critical labs page structure.
Added inline script to set data-metrics attribute for liver panel stats.
srv/api/templates/ui_index.html (Modified)
Added links to both critical labs and liver labs pages for a sample person.
Python Backend

srv/api/dashboard.py (Modified)
Added route /ui/people/{id}/labs/liver serving the new liver panel page template.
Existing /ui/people/{id}/labs/critical route left unchanged.
Added/update handlers for static files and authentication remained verified.
Other

CHANGE_LOG.md (Created and appended with detailed amendments log).
5. Solutions & Troubleshooting

Initial syntax error in labs_critical_v2.js traced to extraneous pasted text; fixed by cleaning the file and providing a minimal safe fallback.
Null pointer failures caused by chart canvas elements missing in dynamically created containers fixed by building DOM elements explicitly and ensuring proper attachment order.
Performance jank via frequent chart recreation mitigated by implementing chart reuse and guarded loading states.
RequestIdleCallback deferral of chart updates introduced Chart.js internal errors; reverted deferral and ensured synchronous update calls with animation disabled to improve smoothness while avoiding crashes.
Added client-side data-metrics attribute to differentiate between liver and critical lab data requests.
Encountered 501 errors for liver metrics fetch due to missing backend support—acknowledged as known backend issue.
Continued logging and debugging steps emphasized at every stage.
Stable UI achieved with reuse and synchronous updates, setting stage for further throttling and downsampling.
6. Outstanding Work

Awaiting further implementation of throttling pointermove and wheel event handlers within attachInteractions to reduce high-duration event handler warnings ([Violation] logs).
Need backend implementation for liver metrics aggregation endpoints to stop 501 responses for liver metrics API calls.
Potential implementation of automatic client-side downsampling to limit chart point counts and memory usage, aiding performance and confirming crash theory.
CSS and UI layout polish to correct “sloppy” layouts and prevent visual jitter.
Final cleanup of verbose debug logging with a focus on functional logs only.
Optionally add favicon to resolve 404 for /favicon.ico requests.
Further integration and unit testing expansions for robustness.
User to test the liver panel page extensively and confirm crash causes, then iterate fixes accordingly.
This summary captures the entire conversation’s technical context, changes made, debugging steps, and next actionable items, enabling seamless continuation of work.

Conversation Summary

Conversation Overview
The conversation centered around the development, debugging, and enhancement of a Health Portal web application's frontend and backend components, primarily focusing on critical and liver lab chart rendering, dashboard UI improvements, routing, and static asset management. The discussion progressed from resolving JavaScript syntax errors in the labs_critical_v2.js script to improving UI link dynamicity, optimizing chart rendering performance, fixing banner rendering on dashboard-related pages, and addressing favicon loading errors.

Active Development
The foremost active work involved debugging and refining the labs_critical_v2.js client script responsible for rendering critical lab charts. This included removing stray non-JavaScript instruction text, defending against null canvas references, and enhancing chart rendering efficiency by reusing existing Chart.js instances instead of recreating them on each render. Further improvements introduced included adding guards to prevent redundant or overlapping network fetches (loadWithAgg function), deferring heavy chart initialization using requestIdleCallback, and dynamically resolving user identifiers (person_id) in URLs. The banner and navigation menu were harmonized to appear consistently on dashboard and related event pages, with proper routing and branding. Finally, favicon serving was corrected to prevent 404 errors.

Technical Stack

Backend: Python FastAPI for API routing and template rendering, with Jinja2 templates for HTML rendering.
Frontend: JavaScript with Chart.js for charting, using defensive programming patterns, async/await for fetch calls, and efficient DOM manipulation.
Static Assets: Served via FastAPI static mount; CSS for layout and styling elements like dashboard grids, banners, and buttons.
Testing: Pytest used for UI-related tests.
Caching: Simple in-memory caching used for dashboard events JSON endpoint response.
Patterns: Single-page viewport-centric rendering, localStorage for UI state, ARIA attributes for accessibility, event delegation, debouncing.
File Operations
Created:
srv/api/static/js/labs_critical_v2.safe.js: A minimal safe JS loader to prevent UI crashes during main script fixes.
Modified:
srv/api/static/js/labs_critical_v2.js: Removed trailing instruction text; added null canvas guards; optimized renderCharts to reuse Chart.js instances; added fetch inflight guards in loadWithAgg; implemented requestIdleCallback deferral for chart creation; dynamically resolved user person_id in UI links.
srv/api/templates/includes/header.html: Added comprehensive navigation links with dynamic person_id or fallback to "me".
srv/api/templates/ui_index.html: Added cards linking to all UI sections, using dynamic person_id.
srv/api/templates/dashboard.html: Ensured consistent header/banner rendering with correct blue banner styling; updated links.
srv/api/templates/events.html: Edited to extend base template and include navigation header for consistent UI.
srv/api/templates/base.html: Added <link rel="icon" href="/favicon.ico" /> to head.
srv/api/main.py: Added FastAPI route to serve /favicon.ico from static files for correct favicon loading.
Referenced but not changed: Static favicon.ico (already present), dashboard_events.py for event routing, dashboard_charts.js for dashboard chart logic, various broken and backup JS files during investigation.
Solutions & Troubleshooting
SyntaxError due to instruction text: Detected and removed accidental appended instructions in labs_critical_v2.js. Introduced a minimal safe JS loader as an interim fix.
Null canvas errors in createChart: Added defensive null canvas guard; restructured makeChartContainer to always create canvases via DOM API; ensured renderCharts associates canvases with their containers correctly.
Performance jank / repeated Chart creation: Optimized chart rendering by reusing existing Chart.js instances, updating data in place, and destroying only obsolete charts.
Redundant fetch guarding: Added element-scoped inflight flags and aggregation guards to avoid repeated network requests and rerenders.
Banner and navigation inconsistencies: Confirmed all pages extend base template, include header.html with full navigation links, fixed path errors (/events → /dashboard/events), and styled banners consistently with blue headers.
Favicon 404 errors: Added favicon route in FastAPI, included favicon link in base template to instruct browsers correctly.
Dynamic user path resolution: Replaced hardcoded UUID person_id with template variables resolving to the current user "me" or passed person_id.
Outstanding Work
Next steps identified by user and assistant:
Further refinements to chart rendering performance, specifically deferred chart creation during idle time using requestIdleCallback.
CSS and UI polish to fix "sloppy" layouts, including canvas sizing, grid consistency, and layout throttling.
Cleanup debug logging for production readiness.
Adding unit/integration tests for UI templating and client-side logic.
Fixing and verifying all page banners and navigation links consistent with the overall UI design, especially for pages like /dashboard/events.
Confirming favicon loading reliability across all UI pages.
Incorporating dynamic person_id resolution fully across the UI to avoid hardcoded paths.
The user has requested to proceed in incremental steps and to focus next on separate improvements with testing after each. The immediate next recommended implementation is to finalize deferring chart creation to idle callbacks for improved UI responsiveness, followed by further CSS layout improvements.

All changes made preserve the existing architecture of FastAPI with Jinja2 templates and Chart.js frontend rendering, enhancing robustness and UX consistency.

This summary encapsulates all key modifications, debugging efforts, files involved, and outstanding work needed to continue development seamlessly with technical precision and context continuity.
## 2025-09-14_15-12-38 — Design scaffold v0.4.1 (FHIR core, critical-labs MV, importer, APIs, docs)
- Added migrations, importer, /labs critical-series, /records browse; docs; guardrails.
