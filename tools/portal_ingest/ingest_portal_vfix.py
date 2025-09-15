#!/usr/bin/env python3
import argparse
import csv
import json
import os
import re
import uuid
import pytz
from datetime import datetime
from dateutil import parser as dtparser

MONTHS = {
    "jan": 1,
    "feb": 2,
    "mar": 3,
    "apr": 4,
    "may": 5,
    "jun": 6,
    "jul": 7,
    "aug": 8,
    "sep": 9,
    "sept": 9,
    "oct": 10,
    "nov": 11,
    "dec": 12,
}


def norm_test(s: str) -> str:
    s = re.sub(r"\s+", " ", (s or "")).strip().upper()
    s = s.replace("’", "'").replace("“", '"').replace("”", '"')
    s = s.replace("TOTAL BILIRUBIN", "BILIRUBIN, TOTAL").replace(
        "DIRECT BILIRUBIN", "BILIRUBIN, DIRECT"
    )
    return s


def parse_num_unit(v: str):
    if v is None:
        return None, None
    s = re.sub(r"\(.*?\)", "", str(v).strip())
    if s.upper().startswith("SEE NOTE"):
        return None, None
    m = re.match(r"^([+-]?\d+(?:\.\d+)?)(?:\s*([A-Za-z/%µ0-9\.\-\^\(\)]*))?$", s)
    if not m:
        return None, None
    val = float(m.group(1))
    unit = (m.group(2) or "").strip() or None
    return val, unit


def parse_portal_text(lines, tz):
    out = []
    cur_dt = None
    provider = None
    page = 1
    order = 0
    skip = re.compile(
        r"^(Continued (on|from) Page|Health\s+Page|This summary|Date of Birth)", re.I
    )
    date_line = re.compile(r"^\s*([A-Za-z]{3,9})\s+(\d{1,2}),\s*(\d{4})\s+(.+?)\s*$")
    for raw in lines:
        line = raw.rstrip("\n")
        if skip.search(line):
            if "Continued on Page" in line:
                page += 1
            continue
        m = date_line.match(line)
        if m:
            mon, d, y, provider = m.groups()
            mkey = mon.strip().lower()[:3]
            if mkey in MONTHS:
                cur_dt = tz.localize(datetime(int(y), MONTHS[mkey], int(d)))
                order = 0
            continue
        if not cur_dt or not provider:
            continue
        parts = re.split(r"\s{2,}", line.strip())
        if len(parts) < 2:
            continue
        test, val = parts[0].strip(), parts[1].strip()
        ref = parts[2].strip() if len(parts) >= 3 else None
        flag = parts[3].strip() if len(parts) >= 4 else None
        out.append(
            dict(
                provider=provider.strip(),
                test_name=test,
                value_text=val,
                reference_text=ref,
                flag=flag,
                effective_time=cur_dt,
                src_line=line,
                src_page=page,
                src_order=order,
            )
        )
        order += 1
    return out


def parse_portal_csv(path, tz):
    import csv as _csv

    rows = []
    with open(path, newline="") as f:
        sniff = f.read(4096)
        f.seek(0)
        dialect = _csv.Sniffer().sniff(sniff, delimiters=",;|\t")
        rd = _csv.DictReader(f, dialect=dialect)

        def get(r, keys, default=None):
            for k in keys:
                if k in r and r[k]:
                    return r[k]
            return default

        for r in rd:
            test = (
                get(r, ["TEST", "Test", "test", "name", "Name", "Test Name"], "") or ""
            ).strip()
            if not test:
                continue
            val = (
                get(r, ["CURRENT", "Value", "value", "Result", "RESULT"], "") or ""
            ).strip()
            ref = get(r, ["REFERENCE", "Reference", "Ref", "ref"])
            flag = get(r, ["FLAG", "Flag"])
            prov = get(r, ["PROVIDER", "Provider"])
            dtxt = get(
                r,
                [
                    "DATE",
                    "Date",
                    "date",
                    "Collected",
                    "COLLECTED",
                    "Date/Time",
                    "Datetime",
                ],
            )
            et = None
            if dtxt:
                try:
                    et = dtparser.parse(dtxt)
                    if et.tzinfo is None:
                        et = tz.localize(et)
                except Exception:
                    et = None
            rows.append(
                dict(
                    provider=prov,
                    test_name=test,
                    value_text=val,
                    reference_text=ref,
                    flag=flag,
                    effective_time=et,
                    src_line=json.dumps(r, ensure_ascii=False),
                    src_page=None,
                    src_order=None,
                )
            )
    return rows


def src_hash(d):
    base = f"{d.get('provider', '')}\x1f{norm_test(d.get('test_name', ''))}\x1f{d.get('value_text', '')}\x1f{d.get('effective_time')}\x1f{d.get('src_line', '')}"
    import hashlib

    return hashlib.sha256(base.encode("utf-8")).hexdigest()


def nk(d):
    return (
        norm_test(d.get("test_name", "")),
        d.get("value_num"),
        (d.get("unit") or "").strip(),
        d.get("effective_time"),
        d.get("provider"),
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--person-id", required=True)
    ap.add_argument("--input", required=True, nargs="+")
    ap.add_argument("--source-file", required=True)
    ap.add_argument("--tz", default="America/New_York")
    ap.add_argument("--dry-run", action="store_true", help="Write CSVs only; no DB.")
    args = ap.parse_args()

    tz = pytz.timezone(args.tz)
    run_id = uuid.uuid4()
    outdir = os.path.join(os.getcwd(), "portal_ingest_out", str(run_id))
    os.makedirs(outdir, exist_ok=True)

    all_rows = []
    rejects = []
    dups = []
    seen = set()
    for p in args.input:
        if not os.path.exists(p):
            print(f"[warn] missing input {p}", flush=True)
            continue
        ext = os.path.splitext(p)[1].lower()
        rows = (
            parse_portal_csv(p, tz)
            if ext in (".csv", ".tsv")
            else parse_portal_text(
                open(p, encoding="utf-8", errors="ignore").readlines(), tz
            )
        )
        for r in rows:
            r["person_id"] = args.person_id
            r["run_id"] = str(run_id)
            r["meta"] = {
                "source_file": args.source_file,
                "imported_at": datetime.now(tz).isoformat(),
            }
            v, u = parse_num_unit(r["value_text"])
            if v is None:
                rejects.append(
                    dict(
                        reason="non-numeric or SEE NOTE",
                        provider=r.get("provider"),
                        raw_text=r.get("src_line"),
                        effective_time=r.get("effective_time"),
                        parsed={
                            "test": r.get("test_name"),
                            "value": r.get("value_text"),
                            "ref": r.get("reference_text"),
                        },
                    )
                )
                continue
            r["value_num"] = v
            r["unit"] = u
            r["code_system"] = "LOCAL"
            r["code"] = norm_test(r["test_name"])
            if not r.get("effective_time"):
                r["effective_time"] = tz.localize(
                    datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                )
            if not r.get("provider"):
                r["provider"] = "Unknown"
            r["src_hash"] = src_hash(r)
            key = nk(r)
            if key in seen:
                dups.append(
                    dict(
                        src_hash=r["src_hash"],
                        reason="within-run duplicate",
                        details={
                            "test": r["test_name"],
                            "value": r["value_num"],
                            "unit": r["unit"],
                        },
                    )
                )
                continue
            seen.add(key)
            all_rows.append(r)

    fields = [
        "run_id",
        "person_id",
        "provider",
        "test_name",
        "value_num",
        "unit",
        "flag",
        "reference_text",
        "effective_time",
        "code_system",
        "code",
        "src_line",
        "src_page",
        "src_order",
        "src_hash",
    ]
    with open(os.path.join(outdir, "staged.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in all_rows:
            w.writerow({k: r.get(k) for k in fields})
    with open(os.path.join(outdir, "duplicates.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["run_id", "src_hash", "reason", "details"])
        w.writeheader()
        for d in dups:
            w.writerow({"run_id": str(run_id), **d})
    with open(os.path.join(outdir, "rejections.csv"), "w", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "run_id",
                "reason",
                "provider",
                "raw_text",
                "effective_time",
                "parsed",
            ],
        )
        w.writeheader()
        for rj in rejects:
            w.writerow({"run_id": str(run_id), **rj})

    summary = {
        "run_id": str(run_id),
        "inputs": args.input,
        "staged_rows": len(all_rows),
        "duplicates": len(dups),
        "rejections": len(rejects),
    }
    with open(os.path.join(outdir, "summary.json"), "w") as f:
        json.dump(summary, f, indent=2, default=str)
    print(json.dumps(summary, indent=2))
    print(f"[dry-run] wrote logs to {outdir}")


if __name__ == "__main__":
    main()
