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
