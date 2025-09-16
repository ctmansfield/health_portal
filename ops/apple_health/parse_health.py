#!/usr/bin/env python3
"""
Apple Health export.xml → FHIR R4 Bundle (Observations)
- Reads <Record> elements from export.xml
- Maps common vitals to LOINC + UCUM
- Emits a transaction Bundle with conditional creates (PUT to deterministic URNs)

Usage:
  python ops/apple_health/parse_health.py /path/to/export.xml output.json [--subject Patient/example]

Notes:
- Only a selected, high-signal subset is mapped to keep it deterministic.
- Unknown/misc records are skipped (with a counter).
"""

import sys, json, uuid, xml.etree.ElementTree as ET
from datetime import datetime, timezone

# Minimal mapping: HealthKit type -> (LOINC code, display, UCUM code, value_kind)
HK_MAP = {
    # Heart Rate (beats/min)
    "HKQuantityTypeIdentifierHeartRate": ("8867-4", "Heart rate", "{beats}/min", "Quantity"),
    # Respiratory rate (breaths/min)
    "HKQuantityTypeIdentifierRespiratoryRate": ("9279-1", "Respiratory rate", "{breaths}/min", "Quantity"),
    # Oxygen saturation (%)
    "HKQuantityTypeIdentifierOxygenSaturation": ("59408-5", "Oxygen saturation in Arterial blood by Pulse oximetry", "%", "Quantity"),
    # Body temperature (Cel)
    "HKQuantityTypeIdentifierBodyTemperature": ("8310-5", "Body temperature", "Cel", "Quantity"),
    # Body mass index (kg/m2)
    "HKQuantityTypeIdentifierBodyMassIndex": ("39156-5", "Body mass index (BMI)", "kg/m2", "Quantity"),
    # Body mass (kg)
    "HKQuantityTypeIdentifierBodyMass": ("29463-7", "Body weight", "kg", "Quantity"),
    # Height (cm → m)
    "HKQuantityTypeIdentifierHeight": ("8302-2", "Body height", "m", "Quantity"),
    # Blood glucose (mg/dL)
    "HKQuantityTypeIdentifierBloodGlucose": ("2339-0", "Glucose [Mass/volume] in Blood", "mg/dL", "Quantity"),
    # Systolic/Diastolic (mm[Hg]) come in paired records
    "HKQuantityTypeIdentifierBloodPressureSystolic": ("8480-6", "Systolic blood pressure", "mm[Hg]", "Quantity"),
    "HKQuantityTypeIdentifierBloodPressureDiastolic": ("8462-4", "Diastolic blood pressure", "mm[Hg]", "Quantity"),
    # Steps (count) -> Observation with valueInteger and unit "1"
    "HKQuantityTypeIdentifierStepCount": ("41950-7", "Number of steps", "1", "Integer"),
    # Resting heart rate
    "HKQuantityTypeIdentifierRestingHeartRate": ("40443-4", "Heart rate resting", "{beats}/min", "Quantity"),
    # VO2 max (mL/kg/min)
    "HKQuantityTypeIdentifierVO2Max": ("41955-2", "VO2 max", "mL/(min.kg)", "Quantity"),
}

def fix_unit(value, unit_code):
    # Apple Health units are typically already UCUM; adjust height cm->m, % keep as %, steps count 'count'->'1'
    if unit_code == "m" and isinstance(value, (int, float)):
        return value, "m"
    return value, unit_code

def parse_datetime(s):
    # Apple uses e.g. 2025-06-01 08:31:00 -0400
    # Convert to ISO 8601
    try:
        # Replace space before offset with 'T'
        s = s.replace(" ", "T", 1)
        # Add colon in offset if missing
        if len(s) >= 5 and (s[-5] in ["+", "-"]) and s[-3] != ":":
            s = s[:-2] + ":" + s[-2:]
        return s
    except Exception:
        return s

def mk_quantity(value, unit_code):
    try:
        v = float(value)
    except Exception:
        return None
    return {
        "value": v,
        "unit": unit_code,
        "system": "http://unitsofmeasure.org",
        "code": unit_code
    }

def mk_integer(value):
    try:
        return int(float(value))
    except Exception:
        return None

def obs_from_record(rec, subject_ref):
    hk_type = rec.get("type")
    if hk_type not in HK_MAP:
        return None

    code, display, unit_code, value_kind = HK_MAP[hk_type]
    start = parse_datetime(rec.get("startDate"))
    end = parse_datetime(rec.get("endDate"))
    eff = start if start == end or not end else end  # prefer end as effective
    src = rec.get("sourceName")

    value = rec.get("value")
    # Height is often in cm in export; if unit is cm, convert to m
    unit = rec.get("unit") or unit_code
    if hk_type == "HKQuantityTypeIdentifierHeight" and unit.lower() in ["cm", "centimeter", "centimeters"]:
        try:
            value = float(value) / 100.0
            unit = "m"
        except Exception:
            pass
    # Build Observation
    obs = {
        "resourceType": "Observation",
        "status": "final",
        "category": [{
            "coding": [{"system":"http://terminology.hl7.org/CodeSystem/observation-category","code":"vital-signs"}]
        }],
        "code": {
            "coding": [{"system":"http://loinc.org","code":code,"display":display}],
            "text": display
        },
        "subject": {"reference": subject_ref},
        "effectiveDateTime": eff
    }

    if value_kind == "Quantity":
        q = mk_quantity(value, unit if unit else unit_code)
        if q is None:
            return None
        obs["valueQuantity"] = q
    elif value_kind == "Integer":
        ival = mk_integer(value)
        if ival is None:
            return None
        obs["valueInteger"] = ival
    else:
        return None

    # Device/source extension (lightweight provenance)
    if src:
        obs.setdefault("extension", []).append({
            "url": "http://hl7.org/fhir/StructureDefinition/observation-deviceCode",
            "valueCodeableConcept": {"text": src}
        })
    return obs

def main():
    if len(sys.argv) < 3:
        print("Usage: parse_health.py <export.xml> <out.json> [--subject Patient/example]", file=sys.stderr)
        sys.exit(2)
    export_path = sys.argv[1]
    out_path = sys.argv[2]
    subj = "Patient/example"
    if len(sys.argv) >= 4 and sys.argv[3].startswith("--subject"):
        parts = sys.argv[3].split("=",1)
        if len(parts)==2 and parts[1]:
            subj = parts[1]

    tree = ET.parse(export_path)
    root = tree.getroot()

    # Namespace handling (Apple export doesn't always require)
    records = root.findall(".//Record")
    skipped = 0
    made = 0
    entries = []

    # Combine paired BP readings by startDate/endDate pair if both present
    bp_buffer = {}
    for rec in records:
        t = rec.get("type")
        if t in ("HKQuantityTypeIdentifierBloodPressureSystolic","HKQuantityTypeIdentifierBloodPressureDiastolic"):
            key = (rec.get("startDate"), rec.get("endDate"))
            bp_buffer.setdefault(key, {})[t] = rec
            continue

        res = obs_from_record(rec, subj)
        if res:
            rid = f"urn:uuid:{uuid.uuid4()}"
            entries.append({"request":{"method":"PUT","url": f"Observation/{rid}"},
                            "fullUrl": rid,
                            "resource": res})
            made += 1
        else:
            skipped += 1

    # Emit BP as a single Observation with components when possible
    for key, pair in bp_buffer.items():
        sys_rec = pair.get("HKQuantityTypeIdentifierBloodPressureSystolic")
        dia_rec = pair.get("HKQuantityTypeIdentifierBloodPressureDiastolic")
        if not (sys_rec and dia_rec):
            # fall back to individual if only one present
            for r in (sys_rec, dia_rec):
                if r:
                    res = obs_from_record(r, subj)
                    if res:
                        rid = f"urn:uuid:{uuid.uuid4()}"
                        entries.append({"request":{"method":"PUT","url": f"Observation/{rid}"},
                                        "fullUrl": rid,
                                        "resource": res})
                        made += 1
            continue

        start, end = key
        eff = start if start == end or not end else end
        src = sys_rec.get("sourceName") or dia_rec.get("sourceName")
        def q(rec):
            unit = rec.get("unit") or "mm[Hg]"
            try:
                v = float(rec.get("value"))
            except Exception:
                return None
            return {"value": v, "unit": unit, "system":"http://unitsofmeasure.org","code": unit}

        comp_sys = q(sys_rec)
        comp_dia = q(dia_rec)
        if not (comp_sys and comp_dia):
            continue

        obs = {
            "resourceType":"Observation",
            "status":"final",
            "category":[{"coding":[{"system":"http://terminology.hl7.org/CodeSystem/observation-category","code":"vital-signs"}]}],
            "code":{"coding":[{"system":"http://loinc.org","code":"85354-9","display":"Blood pressure panel"}],"text":"Blood pressure"},
            "subject":{"reference":subj},
            "effectiveDateTime":eff,
            "component":[
                {"code":{"coding":[{"system":"http://loinc.org","code":"8480-6","display":"Systolic"}]},
                 "valueQuantity":comp_sys},
                {"code":{"coding":[{"system":"http://loinc.org","code":"8462-4","display":"Diastolic"}]},
                 "valueQuantity":comp_dia}
            ]
        }
        if src:
            obs.setdefault("extension", []).append({
                "url": "http://hl7.org/fhir/StructureDefinition/observation-deviceCode",
                "valueCodeableConcept": {"text": src}
            })
        rid = f"urn:uuid:{uuid.uuid4()}"
        entries.append({"request":{"method":"PUT","url": f"Observation/{rid}"},
                        "fullUrl": rid,
                        "resource": obs})
        made += 1

    bundle = {"resourceType":"Bundle","type":"transaction","entry": entries}
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(bundle, f, indent=2)

    print(json.dumps({"made": made, "skipped": skipped, "entries": len(entries)}, indent=2))

if __name__ == "__main__":
    main()
