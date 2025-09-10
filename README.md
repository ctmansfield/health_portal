# Health Portal (backend)

FastAPI + Postgres analytics spine for personal health data (FHIR, Apple Health), with exports.

## Quickstart (dev)

```bash
# 1) Install deps (in venv)
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt

# 2) Start API
export HP_DSN="postgresql://health:health_pw@localhost:55432/health"
uvicorn app.api.main:app --host 0.0.0.0 --port 8800 --reload

# Visit http://localhost:8800/docs

## CI & Contributing
CI (flake8 + pytest) runs on pushes/PRs. See `.github/workflows/ci.yml`.
