#!/usr/bin/env python3
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ADRS = ROOT / "docs" / "architecture" / "ADRs"
INDEX = ADRS / "index.md"

TITLE_RE = re.compile(r"^# +(.+)$")
STATUS_RE = re.compile(r"^(.*?)(—|-) +(.+)$")


def parse_title(s: str):
    m = TITLE_RE.match(s.strip())
    if not m:
        return None, None, None
    full = m.group(1).strip()
    # Expect formats like: ADR-0001 — Title OR ADR-0001 - Title
    parts = re.split(r"\s+[—-]\s+", full, maxsplit=1)
    left = parts[0]
    title = parts[1] if len(parts) > 1 else full
    return left, title, full


def read_first_heading(p: Path):
    try:
        with open(p, "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("# "):
                    return line
    except Exception:
        pass
    return None


def main():
    rows = []
    for p in sorted(ADRS.glob("ADR-*.md")):
        heading = read_first_heading(p)
        left, title, full = parse_title(heading or p.stem)
        rows.append((p.name, title or p.stem, ""))
    lines = [
        "# ADR Index",
        "",
        "| File | Title | Notes |",
        "|------|-------|-------|",
    ]
    for name, title, notes in rows:
        lines.append(f"| `{name}` | {title} | {notes} |")
    INDEX.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote ADR index to {INDEX}")


if __name__ == "__main__":
    main()
