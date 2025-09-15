<!-- HP-START-HERE:BEGIN -->
# 🧭 Health Portal — Start Here

**Last updated:** 2025-09-10

Parallel dev lanes with stable contracts:

- **DB** → canonical JSONB + normalized tables & views
- **Application Layer** → only DB client; OpenAPI v1; rendering/export; sign-out + hash
- **Dashboard** → consumes the API (no DB)

## Quick Links
- Docs Home: `docs/index.md`
- Architecture & ADRs: `docs/explanations/architecture/`
- API Reference: `docs/reference/api/`
- Program & System Design: `docs/explanations/reporting_scaffold/Program_System_Design_Consolidated_v0.1.x.md`
- Workstreams & Interface Contracts: `docs/explanations/reporting_scaffold/Parallel_Workstreams_and_Interface_Contracts.md`
- System Architecture & Design: `docs/explanations/reporting_scaffold/System_Architecture_and_Design.md`
- Platform/System Improvements: `docs/explanations/reporting_scaffold/Platform_System_Improvements.md`
- Changelog: `CHANGELOG.md`
- Contributing (LLM quickstart): `CONTRIBUTING.md`

## API v1
- `GET /reports/{id}`, `/reports/{id}/summary`, `/reports/{id}/patient`
OpenAPI: `api/openapi.genomics_reports.v1.yaml`

## Light Mode
- Toggle: `scripts/hp_light_mode.sh on|off|status`
- Manual commit: `scripts/hp_manual_commit.sh "msg"`

Patches install from **/incoming**. Use:
```bash
WORK=/tmp/health_portal_patches; mkdir -p "$WORK"
tar -xzf /incoming/<bundle>.tar.gz -C "$WORK"
bash "$WORK/<bundle>/patch/*/install.sh"
bash "$WORK/<bundle>/patch/*/verify.sh"
```
<!-- HP-START-HERE:END -->

## About
See Start Here above.
