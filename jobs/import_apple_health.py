#!/usr/bin/env python3
"""
Apple Health export importer.
Usage: python jobs/import_apple_health.py --zip /path/to/export.zip --person-id me --dsn postgresql://...
- Streams export.xml from the zip (handles large files).
- Inserts rows into analytics.data_events.
- Uses analytics.etl_state['apple_last_ts'] to only import new samples.
"""
import argparse, zipfile, os, json, datetime as dt, xml.etree.ElementTree as ET
from hp_etl.events import bulk_insert
from hp_etl.state import get_state, set_state

# LOINC codes for mapping
LOINC = {
    "HeartRate": ("LOINC", "8867-4", "Heart rate", "beats/min"),
    "OxygenSaturation": ("LOINC", "59408-5", "Oxygen saturation", "%"),
    "BodyMass": ("LOINC", "29463-7", "Body weight", "kg"),
    "SystolicBloodPressure": ("LOINC", "8480-6", "Systolic blood pressure", "mm[Hg]"),
    "DiastolicBloodPressure": ("LOINC", "8462-4", "Diastolic blood pressure", "mm[Hg]"),
}

def to_utc(s: str) -> str:
    # Apple uses local w/ offset like 2025-09-09 08:12:34 -0400
    # normalize to ISO Z
    try:
        # e.g., '2025-09-09 08:12:34 -0400'
        dt_local = dt.datetime.strptime(s, "%Y-%m-%d %H:%M:%S %z")
        return dt_local.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    except Exception:
        return None

def parse_record(elem):
    t = elem.attrib.get("type","").split(":")[-1]  # e.g., HKQuantityTypeIdentifierHeartRate
    t = t.replace("HKQuantityTypeIdentifier", "").replace("HKCategoryTypeIdentifier", "")
    start = elem.attrib.get("startDate"); end = elem.attrib.get("endDate")
    val = elem.attrib.get("value"); unit = elem.attrib.get("unit")
    device = elem.attrib.get("sourceName") or elem.attrib.get("device")
    start_utc = to_utc(start) if start else None
    end_utc = to_utc(end) if end else None

    if t in ("SleepAnalysis",):
        # period event
        return {
            "kind": "Sleep",
            "code_system": None, "code": None, "display": "Sleep",
            "effective_time": None, "effective_start": start_utc, "effective_end": end_utc,
            "value_num": None, "value_text": elem.attrib.get("value"), "unit": None,
            "device_id": device, "status": "final",
        }
    if t in ("HeartRate","OxygenSaturation","BodyMass","SystolicBloodPressure","DiastolicBloodPressure"):
        cs, code, disp, default_unit = LOINC[t]
        unit = unit or default_unit
        # instant measurement uses end time if present else start
        eff = end_utc or start_utc
        try:
            vnum = float(val) if val is not None else None
        except Exception:
            vnum = None
        return {
            "kind": "Observation",
            "code_system": cs, "code": code, "display": disp,
            "effective_time": eff, "effective_start": None, "effective_end": None,
            "value_num": vnum, "value_text": None, "unit": unit,
            "device_id": device, "status": "final",
        }
    # skip others for now
    return None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--zip", required=True)
    ap.add_argument("--person-id", default="me")
    ap.add_argument("--dsn", default=None)
    args = ap.parse_args()

    last = get_state("apple_last_ts", args.dsn)
    max_ts_seen = last

    with zipfile.ZipFile(args.zip) as z:
        # find export.xml
        name = next((n for n in z.namelist() if n.endswith("export.xml")), None)
        if not name:
            raise SystemExit("export.xml not found in zip")
        with z.open(name) as f:
            it = ET.iterparse(f, events=("start","end"))
            _, root = next(it)  # get root
            batch = []
            for ev, el in it:
                if ev == "end" and el.tag == "Record":
                    rec = parse_record(el)
                    if rec:
                        eff = rec["effective_time"] or rec["effective_end"]
                        if eff and last and eff <= last:
                            pass
                        else:
                            row = dict(
                                person_id=args.person_id, source="apple_health", raw=json.dumps(el.attrib),
                                meta=json.dumps({"file": name}),
                                **rec
                            )
                            batch.append(row)
                            if eff and (max_ts_seen is None or eff > max_ts_seen):
                                max_ts_seen = eff
                        if len(batch) >= 1000:
                            bulk_insert(batch, args.dsn)
                            batch.clear()
                    el.clear()
                    root.clear()
            if batch:
                bulk_insert(batch, args.dsn)

    if max_ts_seen:
        set_state("apple_last_ts", max_ts_seen, args.dsn)
        print("Updated apple_last_ts ->", max_ts_seen)

if __name__ == "__main__":
    main()
