#!/usr/bin/env python3
import sys
import re
import csv
import unicodedata
import datetime as dt
from pathlib import Path

MONTH_RE = r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2},\s+\d{4}"
date_hdr1 = re.compile(rf"Lab Results\s+({MONTH_RE}).*", re.I)
date_hdr2 = re.compile(
    rf"^\s*({MONTH_RE}).*(Quest|Labcorp|Laborator|Diagnostics)", re.I
)
val_line = re.compile(
    r"^\s*([A-Z0-9][A-Z0-9 \/\-,\(\)\.\+%:]+?)\s{2,}([<>]?\s*\d+(?:\.\d+)?)\s*([A-Za-zµμ/%\(\)10\^\-\.\,]+)?\s*$"
)

SKIP = [
    re.compile(r"^\s*Health\s+.*Page \d+ of \d+", re.I),
    re.compile(r"^\s*This summary displays", re.I),
    re.compile(r"^\s*Continued on Page", re.I),
    re.compile(r"^\s*Test\s+Current\s+Reference", re.I),
    re.compile(r"^\s*Date of Birth:", re.I),
    re.compile(r"^\s*Lab Results\s*$", re.I),
]


def clean(s: str) -> str:
    s = unicodedata.normalize("NFKC", s or "")
    return s.replace("\xa0", " ").replace("\uf765", "").replace("", "E")


def parse_date(s: str):
    for fmt in ("%b %d, %Y", "%B %d, %Y"):
        try:
            return dt.datetime.strptime(s, fmt).date()
        except Exception:
            pass
    return None


def iterable_lines(path: Path):
    # Accept .txt OR try pdftotext -layout for .pdf
    if path.suffix.lower() == ".pdf":
        import subprocess

        proc = subprocess.run(
            ["pdftotext", "-layout", str(path), "-"], check=True, capture_output=True
        )
        txt = proc.stdout.decode("utf-8", "replace")
    else:
        txt = path.read_text(errors="replace")
    for line in txt.splitlines():
        yield clean(line)


def parse_file(path: Path):
    current_date = None
    seen = set()
    for line in iterable_lines(path):
        # date headers
        m = date_hdr1.search(line) or date_hdr2.search(line)
        if m:
            d = parse_date(m.group(1))
            if d:
                current_date = d
            continue
        if (
            not line.strip()
            or any(p.search(line) for p in SKIP)
            or current_date is None
        ):
            continue
        m = val_line.match(line)
        if not m:
            continue
        analyte = m.group(1).strip()
        valtxt = (m.group(2) or "").replace(" ", "").strip()
        unit = (m.group(3) or "").strip()
        try:
            val = float(valtxt.lstrip("<>"))
        except Exception:
            continue  # keep numeric only for labs timeline
        # noon UTC for date-only
        dt_iso = f"{current_date.isoformat()}T12:00:00Z"
        key = (dt_iso, analyte.upper(), val, unit)
        if key in seen:
            continue
        seen.add(key)
        yield (dt_iso, analyte, val, unit)


def main(paths):
    w = csv.writer(sys.stdout)
    w.writerow(["dt", "analyte", "value_num", "unit", "source"])
    for p in paths:
        src = Path(p)
        for dt_iso, analyte, val, unit in parse_file(src):
            w.writerow([dt_iso, analyte, val, unit, f"portal_pdf:{src.name}"])


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: parse_portal_text.py <files...>", file=sys.stderr)
        sys.exit(2)
    main(sys.argv[1:])
