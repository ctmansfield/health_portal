#!/usr/bin/env python3
"""
normalize_to_mdjson.py

Goal: Convert heterogeneous inputs (Portal CSV/TXT, or FHIR bundles/Observations) into
canonical MDJSON rows suitable for staging (analytics.lab_ingest_raw_mdjson) and later
load into analytics.data_events_new via SQL.

MDJSON schema per row:
{
  "person_id": "<string>",
  "effective_time": "<ISO 8601 UTC or tz-aware>",
  "code_system": "LOINC" | "LOCAL",
  "code": "<code>",
  "display": "<human-readable label>",
  "value_num": <float|null>,
  "value_text": "<string|null>",
  "unit": "<string|null>",
  "status": "<string|null>",
  "source": "portal|fhir|mdjson",
  "raw": { ... original payload ... },
  "meta": { ... run_id, source_file, provider, etc. ... }
}

Writes a newline-delimited JSON file (NDJSON) to stdout or a path.

Usage examples:
  python tools/portal_ingest/normalize_to_mdjson.py --person-id me --input portal.csv --source portal > out.ndjson
  python tools/portal_ingest/normalize_to_mdjson.py --person-id me --input fhir_bundle.json --source fhir > out.ndjson
"""

import argparse
import csv
import json
import os
import re
import sys
from datetime import datetime
from dateutil import parser as dtparser
import pytz

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
MAP_PATH = os.path.join(THIS_DIR, "mappings", "loinc_map.csv")

MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "sept": 9, "oct": 10, "nov": 11, "dec": 12,
}


def load_loinc_map(path: str):
    mapping = []
    if not os.path.exists(path):
        return mapping
    with open(path, newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            pat = (row.get("pattern", "") or "").strip().upper()
            if not pat:
                continue
            mapping.append({
                "pattern": pat,
                "loinc_code": (row.get("loinc_code", "") or "").strip(),
                "canonical_name": (row.get("canonical_name", "") or "").strip(),
                "unit_hint": (row.get("unit_hint", "") or "").strip(),
            })
    return mapping


def normalize_test_name(name: str) -> str:
    s = re.sub(r"\s+", " ", (name or "")).strip().upper()
    s = s.replace("’", "'").replace("“", '"').replace("”", '"')
    s = s.replace("TOTAL BILIRUBIN", "BILIRUBIN, TOTAL")
    s = s.replace("DIRECT BILIRUBIN", "BILIRUBIN, DIRECT")
    return s


def map_loinc(test_name: str, mapping):
    n = normalize_test_name(test_name)
    for m in mapping:
        if n == m["pattern"]:
            return m["loinc_code"], m
    for m in mapping:
        if m["pattern"] and m["pattern"] in n:
            return m["loinc_code"], m
    return None, None


def parse_number_and_unit(val: str):
    if val is None:
        return None, None
    s = str(val).strip()
    if s.upper().startswith("SEE NOTE"):
        return None, None
    s = re.sub(r"\(.*?\)", "", s).strip()
    m = re.match(r"^([+-]?\d+(?:\.\d+)?)\s*([A-Za-z/µ%0-9\.\-\^\(\)]*)$", s)
    if not m:
        m = re.match(r"^([+-]?\d+(?:\.\d+)?)\s*%$", s)
        if m:
            return float(m.group(1)), "%"
        return None, None
    val = float(m.group(1))
    unit = m.group(2).strip() or None
    return val, unit


def parse_portal_text(lines, default_tz, person_id, source):
    results = []
    cur_date = None
    cur_provider = None
    page = 1
    order = 0

    skip_re = re.compile(r"^(Continued on Page|Continued from Page|Health\s+Page|This summary|Date of Birth)", re.I)
    date_line_re = re.compile(r"^\s*([A-Za-z]{3,9})\s+(\d{1,2}),\s*(\d{4})\s+(.+?)\s*$")

    for raw in lines:
        line = raw.rstrip("\n")
        if skip_re.search(line):
            if "Continued on Page" in line:
                page += 1
            continue
        m = date_line_re.match(line)
        if m:
            mon, d, y, provider = m.groups()
            mkey = mon.strip().lower()[:3]
            if mkey not in MONTHS:
                continue
            cur_date = default_tz.localize(datetime(int(y), MONTHS[mkey], int(d)))
            cur_provider = provider.strip()
            order = 0
            continue
        if not cur_date:
            continue
        parts = re.split(r"\s{2,}", line.strip())
        if len(parts) < 2:
            continue
        test = parts[0].strip()
        val = parts[1].strip()
        value_num, unit = parse_number_and_unit(val)
        code, meta = map_loinc(test, load_loinc_map(MAP_PATH))
        code_system = "LOINC" if code else "LOCAL"
        code = code or normalize_test_name(test)
        display = test
        result = {
            "person_id": person_id,
            "effective_time": cur_date.isoformat(),
            "code_system": code_system,
            "code": code,
            "display": display,
            "value_num": value_num,
            "value_text": None if value_num is not None else val,
            "unit": unit,
            "status": None,
            "source": source,
            "raw": {"line": line, "page": page, "order": order, "provider": cur_provider},
            "meta": {"provider": cur_provider}
        }
        order += 1
        results.append(result)
    return results


def parse_portal_csv(path, default_tz, person_id, source):
    rows = []
    with open(path, newline="") as f:
        r = csv.DictReader(f)
        def get(row, keys, default=None):
            for k in keys:
                if k in row and row[k]:
                    return row[k]
            return default
        for row in r:
            test = (get(row, ["TEST","Test","test","name","Name"], "") or "").strip()
            if not test:
                continue
            val = (get(row, ["CURRENT","Value","value","Result","RESULT"], "") or "").strip()
            provider = get(row, ["PROVIDER","Provider"], None)
            dtxt = get(row, ["DATE","Date","date","Collected","COLLECTED"], None)
            etime = None
            if dtxt:
                try:
                    etime = dtparser.parse(dtxt)
                except Exception:
                    etime = None
            if etime and etime.tzinfo is None:
                etime = default_tz.localize(etime)
            value_num, unit = parse_number_and_unit(val)
            code, meta = map_loinc(test, load_loinc_map(MAP_PATH))
            code_system = "LOINC" if code else "LOCAL"
            code = code or normalize_test_name(test)
            display = test
            rows.append({
                "person_id": person_id,
                "effective_time": (etime or default_tz.localize(datetime.now())).isoformat(),
                "code_system": code_system,
                "code": code,
                "display": display,
                "value_num": value_num,
                "value_text": None if value_num is not None else val,
                "unit": unit,
                "status": None,
                "source": source,
                "raw": row,
                "meta": {"provider": provider}
            })
    return rows


def parse_fhir_json(path, person_id_default=None):
    # Accept a single Observation resource, or a Bundle with entries
    with open(path, "r", encoding="utf-8") as f:
        doc = json.load(f)
    out = []
    def to_mdjson(obs: dict):
        if not isinstance(obs, dict):
            return None
        if obs.get("resourceType") != "Observation":
            return None
        # subject reference may hold Patient/id
        subj = ((obs.get("subject") or {}).get("reference") or "")
        pid = re.sub(r"^Patient/", "", subj) or person_id_default
        # time
        et = obs.get("effectiveDateTime") or ((obs.get("effectivePeriod") or {}).get("start"))
        # coding
        code = ((obs.get("code") or {}).get("coding") or [{}])[0]
        code_system = (code.get("system") or "").lower() or None
        code_code = code.get("code")
        display = code.get("display") or (obs.get("code") or {}).get("text")
        # values
        vq = obs.get("valueQuantity") or {}
        value_num = vq.get("value")
        unit = vq.get("unit")
        value_text = obs.get("valueString") or (obs.get("valueCodeableConcept") or {}).get("text")
        status = obs.get("status")
        return {
            "person_id": pid,
            "effective_time": et,
            "code_system": code_system,
            "code": code_code,
            "display": display,
            "value_num": float(value_num) if value_num is not None else None,
            "value_text": value_text,
            "unit": unit,
            "status": status,
            "source": "fhir",
            "raw": obs,
            "meta": None,
        }
    if doc.get("resourceType") == "Bundle":
        for e in (doc.get("entry") or []):
            res = e.get("resource")
            m = to_mdjson(res)
            if m:
                out.append(m)
    else:
        m = to_mdjson(doc)
        if m:
            out.append(m)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--person-id", help="Default person_id if not found in input")
    ap.add_argument("--input", required=True, nargs="+", help="Input file(s): CSV/TXT portal or FHIR JSON/Bundle")
    ap.add_argument("--source", default="portal", help="Source label: portal|fhir|mdjson")
    ap.add_argument("--tz", default="America/New_York", help="Timezone for dates without TZ")
    ap.add_argument("--out", help="Output file for NDJSON; default stdout")
    args = ap.parse_args()

    tz = pytz.timezone(args.tz)
    mapping = load_loinc_map(MAP_PATH)
    all_rows = []

    for path in args.input:
        ext = os.path.splitext(path)[1].lower()
        if ext in (".csv", ".tsv"):
            rows = parse_portal_csv(path, tz, args.person_id, args.source)
        elif ext in (".json", ".ndjson"):
            rows = parse_fhir_json(path, person_id_default=args.person_id)
        else:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                rows = parse_portal_text(f.readlines(), tz, args.person_id, args.source)
        all_rows.extend(rows)

    # Normalize timestamps to ISO strings; ensure tz-aware
    out_rows = []
    for r in all_rows:
        et = r.get("effective_time")
        if et:
            try:
                dt = dtparser.parse(et) if isinstance(et, str) else et
                if dt.tzinfo is None:
                    dt = tz.localize(dt)
                et_iso = dt.isoformat()
            except Exception:
                et_iso = tz.localize(datetime.now()).isoformat()
        else:
            et_iso = tz.localize(datetime.now()).isoformat()
        r["effective_time"] = et_iso
        out_rows.append(r)

    # Output NDJSON
    sink = open(args.out, "w") if args.out else sys.stdout
    try:
        for r in out_rows:
            sink.write(json.dumps(r, ensure_ascii=False) + "\n")
    finally:
        if args.out:
            sink.close()

if __name__ == "__main__":
    main()
