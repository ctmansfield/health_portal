#!/usr/bin/env python3
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs" / "reference" / "glossary_synonyms.json"

SYN = {
    "critical labs": ["labs critical", "app-9", "critical-series"],
    "etl": ["ingest", "import", "pipeline"],
    "dashboard": ["ui dashboard", "summary"],
}


def main():
    OUT.write_text(json.dumps(SYN, indent=2), encoding="utf-8")
    print(f"Wrote glossary synonyms to {OUT}")


if __name__ == "__main__":
    main()
