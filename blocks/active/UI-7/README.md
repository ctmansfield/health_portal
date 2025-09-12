# UI-7 — Reference Bands + Legend + Export-all CSV

**Component:** ui
**Status:** active
**Assignee:** Chad
**Opened:** 2025-09-12T04:39:50.431027Z

## Context & Links

## Paths You May Touch
- app/templates/components/labs_critical_page.html
- app/static/js/labs_critical_v2.js
- srv/api/reports.py

## Acceptance Criteria
- [ ] Bands render using ref_low/ref_high when present
- [ ] Legend toggles hide/show series lines & points; persisted
- [ ] 'Export-all CSV includes only visible series with headers: timestamp_utc,metric,value,unit,flag'
- [ ] Works for daily and hourly aggregations
- [ ] No layout overlap with summary pane (respects UI-6 grid)
- [ ] tests/test_ui_labs_critical.py passes
