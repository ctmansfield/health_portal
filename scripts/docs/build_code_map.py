#!/usr/bin/env python3
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs" / "reference" / "code_map.json"

# Seed a minimal code→doc map; contributors can extend this over time.
SEED = {
    "srv/api": "docs/reference/api/README.md",
    "services/healthdb-pg-0001": "docs/reference/contracts/README.md",
    "tools/portal_ingest": "docs/how-to/Portal_Ingest.md",
    "scripts/cron": "docs/runbooks/Backup_Restore.md",
}


def main():
    OUT.write_text(json.dumps(SEED, indent=2), encoding="utf-8")
    print(f"Wrote code map to {OUT}")


if __name__ == "__main__":
    main()
