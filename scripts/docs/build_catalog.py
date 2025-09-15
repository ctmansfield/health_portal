#!/usr/bin/env python3
import os
import re
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs"
CATALOG = DOCS / "catalog.json"

HEADING_RE = re.compile(r"^# +(.+)$")
FRONT_MATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)

SECTIONS = {
    "how-to": "how-to",
    "reference": "reference",
    "explanations": "explanations",
    "runbooks": "runbooks",
    "changes": "changes",
    "tutorials": "tutorials",
}


def extract_front_matter(text: str):
    m = FRONT_MATTER_RE.match(text)
    if not m:
        return {}, text
    import yaml  # allowed offline parsing

    try:
        data = yaml.safe_load(m.group(1)) or {}
    except Exception:
        data = {}
    rest = text[m.end() :]
    return data, rest


def first_heading(text: str, default: str):
    for line in text.splitlines():
        line = line.strip()
        m = HEADING_RE.match(line)
        if m:
            return m.group(1).strip()
    return default


def first_paragraph(text: str):
    parts = [p.strip() for p in text.split("\n\n") if p.strip()]
    return parts[0] if parts else ""


def detect_section(path: Path):
    try:
        return SECTIONS.get(path.relative_to(DOCS).parts[0], "docs")
    except Exception:
        return "docs"


def main():
    entries = []
    for path in DOCS.rglob("*.md"):
        if path.name == "index.md":
            continue
        rel = str(path.relative_to(DOCS)).replace("\\", "/")
        try:
            text = path.read_text(encoding="utf-8")
        except Exception:
            text = ""
        fm, body = extract_front_matter(text)
        title = fm.get("title") or first_heading(
            body or text, default=path.stem.replace("_", " ").replace("-", " ").title()
        )
        summary = fm.get("summary") or first_paragraph(body)
        owner = fm.get("owner")
        tags = fm.get("tags") or []
        section = fm.get("section") or detect_section(path)
        entries.append(
            {
                "path": rel,
                "title": title,
                "section": section,
                "owner": owner,
                "tags": tags,
                "summary": summary,
            }
        )
    CATALOG.write_text(json.dumps({"documents": entries}, indent=2), encoding="utf-8")
    print(f"Wrote catalog with {len(entries)} documents to {CATALOG}")


if __name__ == "__main__":
    main()
