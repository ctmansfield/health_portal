#!/usr/bin/env python3
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs" / "reference" / "contracts" / "index.json"
API_DIR = ROOT / "api"
DB_DIR = ROOT / "services" / "healthdb-pg-0001"
UI_DIRS = [ROOT / "srv" / "api" / "templates", ROOT / "srv" / "api" / "static"]


def build_api():
    items = []
    for p in API_DIR.glob("*.yaml"):
        items.append({"type": "openapi", "path": str(p.relative_to(ROOT))})
    return items


def build_db():
    items = []
    for p in (DB_DIR / "init").glob("*.sql"):
        items.append({"type": "db-init-sql", "path": str(p.relative_to(ROOT))})
    for p in (DB_DIR / "migrations").glob("*.sql"):
        items.append({"type": "db-migration-sql", "path": str(p.relative_to(ROOT))})
    return items


def build_ui():
    items = []
    for base in UI_DIRS:
        for p in base.rglob("*"):
            if p.suffix in {".html", ".js", ".css"}:
                items.append({"type": "ui-asset", "path": str(p.relative_to(ROOT))})
    return items


def main():
    registry = {
        "api": build_api(),
        "db": build_db(),
        "ui": build_ui(),
    }
    OUT.write_text(json.dumps(registry, indent=2), encoding="utf-8")
    print(f"Wrote contracts registry to {OUT}")


if __name__ == "__main__":
    main()
