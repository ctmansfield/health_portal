#!/usr/bin/env python3
import json
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[2]
CODE_MAP = ROOT / "docs" / "reference" / "code_map.json"
CATALOG = ROOT / "docs" / "catalog.json"
OUT = ROOT / "docs" / "status" / "staleness.json"


def main():
    status = {"generated_at": datetime.utcnow().isoformat() + "Z", "entries": []}
    code_map = (
        json.loads(CODE_MAP.read_text(encoding="utf-8")) if CODE_MAP.exists() else {}
    )
    catalog = (
        json.loads(CATALOG.read_text(encoding="utf-8"))
        if CATALOG.exists()
        else {"documents": []}
    )
    _doc_index = {d["path"]: d for d in catalog.get("documents", [])}

    for code_path, doc_path in code_map.items():
        code_abs = ROOT / code_path
        doc_abs = ROOT / doc_path
        code_mtime = max(
            (p.stat().st_mtime for p in code_abs.rglob("*") if p.is_file()), default=0
        )
        doc_mtime = doc_abs.stat().st_mtime if doc_abs.exists() else 0
        stale = code_mtime > doc_mtime
        status["entries"].append(
            {
                "code_path": code_path,
                "doc_path": doc_path,
                "code_last_modified": code_mtime,
                "doc_last_modified": doc_mtime,
                "stale": stale,
            }
        )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(status, indent=2), encoding="utf-8")
    print(f"Wrote staleness report to {OUT}")


if __name__ == "__main__":
    main()
