# Observability & SLOs

## SLI / SLO targets (initial)
- **API availability**: 99.5% monthly
- **p95 GET /reports/{id} latency**: ≤ 800 ms (staging baseline + 20%)
- **Render success rate**: ≥ 99.8% on valid payloads
- **Ingest validation failure rate**: < 1% (non-synthetic)

## Metrics to collect
- HTTP: request rate, latency histograms, error ratios per route
- Rendering: render time, cache hit rate, snapshot diffs
- Ingest: validations/sec, failure categories
- Export: FHIR bundle count, validation errors
- DB: slow query count, connections, locks

## Dashboards
- API performance; Rendering & PDF; Ingest & Validation; DB health.
