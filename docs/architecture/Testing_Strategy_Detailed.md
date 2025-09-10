# Testing Strategy — Detailed Matrix

| Area | Test | DoD |
|---|---|---|
| Schema | jsonschema fixtures (+/-) | invalids rejected; valids pass |
| Renderer | snapshot (clinician/patient) | byte-stable HTML; print CSS check |
| API | contract tests from OpenAPI | 2xx shapes match; error shapes documented |
| DB | migration up/down | rollback ok; views intact |
| Perf | p95 route latency | within SLO; regression budget |
| Security | access roles | least privilege verified |
