# How-To — Portal Lab Parser to Postgres

Install
```bash
# from repo root
./install.sh
```

Run
```bash
# 1) Clean CSV first (preferred if available)
source .venv-portal-ingest/bin/activate
python tools/portal_ingest/ingest_portal.py --dsn "$HP_PG_DSN" --person-id "person_chad" --input "/mnt/data/portal_20250625_clean.csv" --source-file "portal_20250625_clean.csv"

# 2) Or parse the raw text export directly
python tools/portal_ingest/ingest_portal.py --dsn "$HP_PG_DSN" --person-id "person_chad" --input "/mnt/data/portal_20250625.txt" --source-file "portal_20250625.txt"
```

Notes
- DSN: env HP_PG_DSN (e.g., postgresql://user:pass@localhost:5432/healthdb)
- TZ default America/New_York; override with --tz
- Idempotent: within-run dedupe + natural-key merge
- Unknown tests import as LOCAL codes; update mappings/mappings/loinc_map.csv and re-run

Verify
```bash
./verify.sh person_chad 90
```

Reprocess excluded data
- Fix tools/portal_ingest/mappings/loinc_map.csv and re-run the same file
- You can export from ingest_portal.rejections and re-feed the corrected CSV with --input
