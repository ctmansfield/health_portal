# Health Portal API

A minimal read-only FastAPI service exposing recent events and AI findings.

## Quickstart

```bash
cd srv/api
pip install -r requirements.txt
export HP_DSN="postgresql://health:health_pw@localhost:55432/health"
uvicorn srv.api.main:app --host 127.0.0.1 --port 8081 &
```

## Endpoints

- `GET /healthz`
- `GET /events/recent?limit=100&person_id=me` — recent events (max 500)
- `GET /findings/daily?days=30&person_id=me` — AI findings from past N days (max 90)

## Example Usage

```bash
curl 'http://127.0.0.1:8081/healthz'
curl 'http://127.0.0.1:8081/events/recent?limit=2'
curl 'http://127.0.0.1:8081/findings/daily?days=2'
```

## Notes
- All connections use env HP_DSN.
- No authentication: designed for local network behind firewall.
