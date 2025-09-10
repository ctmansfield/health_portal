<!-- HP-START-HERE:BEGIN -->
# 🧭 Health Portal — Start Here

**Last updated:** 2025-09-10

This repo is organized for **parallel development** across three components with stable contracts:

- **DB** → canonical JSONB + normalized tables & views (no direct dashboard access)
- **Application Layer** → the only DB client; exposes the **OpenAPI v1** Reports API; rendering/export; sign-out + payload hash
- **Dashboard** → consumes the API for clinician and patient-mode views

## Quick Links
- **Program & System Design (Consolidated):** `docs/reporting_scaffold/Program_System_Design_Consolidated_v0.1.x.md`
- **Parallel Workstreams & Interface Contracts:** `docs/reporting_scaffold/Parallel_Workstreams_and_Interface_Contracts.md`
- **System Architecture & Design:** `docs/reporting_scaffold/System_Architecture_and_Design.md`
- **Architecture (expanded) & ADRs:** `docs/architecture/` (C4 diagrams, Threat Model, ADRs, SLOs, Runbooks)
- **Platform & System Improvements:** `docs/reporting_scaffold/Platform_System_Improvements.md` and `docs/architecture/Testing_Strategy_Detailed.md`
- **Contributing (humans + LLMs):** `CONTRIBUTING.md` (boundaries, prompt, PR checklist)

## API Contracts (read-only v1)
- `GET /reports/{id}` — clinician payload
- `GET /reports/{id}/summary` — dashboard card
- `GET /reports/{id}/patient` — patient-mode

OpenAPI file: `api/openapi.genomics_reports.v1.yaml` (semantic versioning via `Accept-Version`).

## Optional: “Light Mode” (no CI friction)
- Toggle automation: `scripts/hp_light_mode.sh on|off|status`
- Manual commit helper: `scripts/hp_manual_commit.sh "your message"`

**Note:** Patches are delivered via **/incoming**. Install using:
```bash
WORK=/tmp/health_portal_patches; mkdir -p "$WORK"
tar -xzf /incoming/<bundle>.tar.gz -C "$WORK"
bash "$WORK/<bundle>/patch/*/install.sh"
bash "$WORK/<bundle>/patch/*/verify.sh"
```
<!-- HP-START-HERE:END -->

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
