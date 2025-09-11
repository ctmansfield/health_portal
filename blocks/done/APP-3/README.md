# APP-3 — GET /reports/{id}/summary

Contract-compliant implementation backed by `report_exec_summary`.

## Curl

```bash
RID="<uuid>"
curl -i http://localhost:8000/reports/$RID/summary
```

## Tests

```bash
pytest -q -k "reports and summary" || pytest -q -k "report and summary"
```
