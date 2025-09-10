#!/usr/bin/env bash
set -euo pipefail
cd /mnt/nas_storage/repos/health_portal
. .venv/bin/activate || true
# Example calls; adjust ZIP path as you automate exports
# python jobs/import_apple_health.py --zip /path/to/export.zip --person-id me --dsn postgresql://health:health_pw@localhost:55432/health
python jobs/mirror_fhir_observations.py --dsn postgresql://health:health_pw@localhost:55432/health
