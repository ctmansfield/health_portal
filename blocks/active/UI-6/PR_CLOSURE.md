Title: UI-6 / dashboard & labs charts — PR closure notes

Summary

This PR added the UI-6 interaction work and several fixes/cleanup to stabilize dashboard and labs charts, the Summary panel, and the supporting client-side tooling. It also added a small integration test for the dashboard layout.

What I changed (high level)

- New / moved JS
  - Added: srv/api/static/js/dashboard_charts.fixed.js (intermediate temporary file)
  - Added/updated: srv/api/static/js/dashboard_charts.js — primary dashboard chart logic (DPR-safe sizing, debounced resize, Chart.js creation, sparklines)
  - Added: srv/api/static/js/dashboard_charts.v2.js (if present as an alternate) — iterative versions kept while debugging
  - Added: srv/api/static/js/labs_critical_v2.js (earlier edits) — labs page interactions (zoom/brush, pan, agg toggle, persistence)

- Templates
  - Modified: srv/api/templates/dashboard.html
    - Replaced old layout with a two-column .dashboard-main grid (chart panel + summary panel)
    - Restored the summary markup (Latest HR, Min SpO2, sparklines, SpO2 chart)
    - Exposed hrLabels/hrData/spo2Data as window globals for client JS and loads dashboard script
  - Modified: app/templates/components/labs_critical_page.html (added agg default attr + header link)

- CSS
  - Modified: srv/api/static/style.css
    - Added .dashboard-main, .panel, .chart-wrap, summary-card rules per UI-6 acceptance
    - Added canvas and sparkline styles, pointer-event fixes, and layout sizing (60%/40% grid)

- Tests
  - Added: tests/test_ui_dashboard_layout.py — asserts presence of .dashboard-main, .chart-wrap, .summary-card, and sparkline canvases
  - Existing tests run: pytest -q -> 17 passed, 1 skipped locally (after iterative changes)

- Labs page UX
  - app/static/js/labs_critical_v2.js — implemented zoom (drag), pan (shift+wheel), agg persistence (hp:labs:agg:<person>), preview/live mode, CSV export; Chart creation is DPR-safe and interaction-aware

- Misc
  - Fixed: srv/api/dashboard.py import of JSONResponse and preview endpoint (so preview no longer 500)
  - Created robust client-side caching in dashboard/labs scripts for preview content

What I iterated on during debugging

- The dashboard JS was iteratively rewritten several times to avoid a canvas/ResizeObserver feedback loop that caused charts to stretch vertically over time. The final approach used in srv/api/static/js/dashboard_charts.js is:
  - DPR-backed sizeCanvas() which only updates the canvas backing store if dimensions actually changed
  - createChart(cv, cfg) that constructs Chart.js with the canvas 2D context and falls back to a lightweight canvas drawer if Chart.js isn't available
  - debounced resize handler that calls chart.resize() + chart.update() (no destructive recreate while resizing)
  - sparklines were given background fill and interaction options for hover/tooltips

Commands to run locally

1) Install/run tests
   . .venv/bin/activate
   pytest -q

2) Run the app
   . .venv/bin/activate
   uvicorn srv.api.main:app --host 0.0.0.0 --port 8800 --reload

3) Dev verification
   - Dashboard: http://localhost:8800/dashboard
     - Verify the two-panel layout (chart + summary) on desktop and stacked on narrow widths
     - Verify big chart interactivity (hover/tooltips)
     - Verify sparklines show background + hover and do not overlap the summary card
   - Labs: http://localhost:8800/ui/people/me/labs/critical?preview=1
     - Verify zoom (click+drag), pan (shift+wheel), agg toggle persistence and CSV export

Known issues & next steps

- During development there were multiple intermediate files and versions (dashboard_charts.fixed.js, dashboard_charts.v2.js). Only the final srv/api/static/js/dashboard_charts.js is intended to be used; other files (if present) can be removed.
- If you still see static sparklines:
  - Hard-refresh with DevTools network cache disabled, then re-check Console for errors.
  - Run the quick Console checks I suggested (typeof Chart, lengths of hrLabels/hrData/spo2Data, and presence of cv._chart for sparklines).
- If you prefer Chart.js to handle responsive sizing internally (responsive:true), we can switch designs: let Chart be responsive and use a throttled redraw strategy rather than manual backing-store manipulation — tradeoff is less direct DPR control but simpler code.

Files touched (summary)

- Added/Edited (frontend):
  - srv/api/static/js/dashboard_charts.js (final)
  - srv/api/static/js/dashboard_charts.fixed.js (intermediate)
  - srv/api/static/js/labs_critical_v2.js (labs interactions)
  - app/static/js/labs_critical_v2.js (mirror)

- Templates:
  - srv/api/templates/dashboard.html (rewritten to .dashboard-main + chart-wrap + summary)
  - app/templates/components/labs_critical_page.html (toolbar + agg attr + header link)

- CSS:
  - srv/api/static/style.css (dashboard layout and canvas fixes)

- Tests:
  - tests/test_ui_dashboard_layout.py (new)

Closure notes

- The core feature (UI-6: zoom/pan + agg toggle) is implemented for labs and dashboard charts are responsive and DPR-correct.
- I iterated heavily to avoid ResizeObserver / canvas feedback loops. The final approach should be stable across modern browsers.

If you want, I can:
- Remove intermediate JS files (dashboard_charts.fixed.js) and clean up repo history.
- Add a small automated integration test that starts the app and checks canvas rendering in headless browser (Selenium / Playwright) if you want stronger verification.

-- End of PR closure
