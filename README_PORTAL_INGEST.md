
# Portal Lab Parser → Postgres (analytics.data_events)

This drop-in adds:
- an `ingest_portal` schema for staging + audit logs
- a Python CLI (`tools/portal_ingest/ingest_portal.py`) that parses your portal text or the cleaned CSV
- a safe merge into `analytics.data_events` with LOINC mapping when available
- duplicate + rejection logs (DB tables and CSV files per run)

## Install

```bash
# from repo root
./install.sh
```

## Run (examples)

```bash
# 1) Clean CSV first (preferred if available)
source .venv-portal-ingest/bin/activate
python tools/portal_ingest/ingest_portal.py   --dsn "$HP_PG_DSN"   --person-id "person_chad"   --input "/mnt/data/portal_20250625_clean.csv"   --source-file "portal_20250625_clean.csv"

# 2) Or parse the raw text export directly
python tools/portal_ingest/ingest_portal.py   --dsn "$HP_PG_DSN"   --person-id "person_chad"   --input "/mnt/data/portal_20250625.txt"   --source-file "portal_20250625.txt"
```

**Notes**

- DSN comes from env var `HP_PG_DSN` (e.g., `postgresql://user:pass@localhost:5432/healthdb`).
- Timezone defaults to `America/New_York`; override with `--tz` if needed.
- Idempotent: within-run dedupe + natural-key merge into `analytics.data_events`.
- Unknown tests import under `code_system='LOCAL'` with `code=<normalized test name>`; you can later map them by extending `mappings/loinc_map.csv` and re-importing the `rejections` backlog.
- Every run writes CSV logs to `./portal_ingest_out/<run_id>/`:
  - `staged.csv` (rows destined for analytics)
  - `duplicates.csv`
  - `rejections.csv`
  - `summary.json`

## Verify

```bash
./verify.sh person_chad 90
```

## Reprocessing excluded data

Fix/extend `tools/portal_ingest/mappings/loinc_map.csv` and re-run the same file.
You can also re-stage previously rejected rows by exporting from `ingest_portal.rejections` then re-feeding the corrected CSV via `--input`.

