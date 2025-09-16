#!/usr/bin/env python3
import sys, json, uuid, xml.etree.ElementTree as ET

HK_MAP = {
    "HKQuantityTypeIdentifierHeartRate": ("8867-4", "Heart rate", "{beats}/min", "Quantity"),
    "HKQuantityTypeIdentifierRespiratoryRate": ("9279-1", "Respiratory rate", "{breaths}/min", "Quantity"),
    "HKQuantityTypeIdentifierOxygenSaturation": ("59408-5", "Oxygen saturation in Arterial blood by Pulse oximetry", "%", "Quantity"),
    "HKQuantityTypeIdentifierBodyTemperature": ("8310-5", "Body temperature", "Cel", "Quantity"),
    "HKQuantityTypeIdentifierBodyMassIndex": ("39156-5", "Body mass index (BMI)", "kg/m2", "Quantity"),
    "HKQuantityTypeIdentifierBodyMass": ("29463-7", "Body weight", "kg", "Quantity"),
    "HKQuantityTypeIdentifierHeight": ("8302-2", "Body height", "m", "Quantity"),
    "HKQuantityTypeIdentifierBloodGlucose": ("2339-0", "Glucose [Mass/volume] in Blood", "mg/dL", "Quantity"),
    "HKQuantityTypeIdentifierBloodPressureSystolic": ("8480-6", "Systolic blood pressure", "mm[Hg]", "Quantity"),
    "HKQuantityTypeIdentifierBloodPressureDiastolic": ("8462-4", "Diastolic blood pressure", "mm[Hg]", "Quantity"),
    "HKQuantityTypeIdentifierStepCount": ("41950-7", "Number of steps", "1", "Integer"),
    "HKQuantityTypeIdentifierRestingHeartRate": ("40443-4", "Heart rate resting", "{beats}/min", "Quantity"),
    "HKQuantityTypeIdentifierVO2Max": ("41955-2", "VO2 max", "mL/(min.kg)", "Quantity"),
}

def parse_datetime(s):
    s = s.replace(" ", "T", 1)
    if len(s) >= 5 and (s[-5] in "+-") and s[-3] != ":":
        s = s[:-2] + ":" + s[-2:]
    return s

def mk_quantity(value, unit_code):
    try:
        v = float(value)
    except Exception:
        return None
    return {"value": v, "unit": unit_code, "system":"http://unitsofmeasure.org", "code": unit_code}

def mk_integer(value):
    try:
        return int(float(value))
    except Exception:
        return None

def obs_from_record(rec, subject_ref):
    hk_type = rec.get("type")
    if hk_type not in HK_MAP:
        return None
    code, display, unit_code, kind = HK_MAP[hk_type]
    start = parse_datetime(rec.get("startDate"))
    end = parse_datetime(rec.get("endDate"))
    eff = end or start
    value = rec.get("value")
    unit = rec.get("unit") or unit_code
    if hk_type == "HKQuantityTypeIdentifierHeight" and unit.lower() in ("cm","centimeter","centimeters"):
        try:
            value = float(value) / 100.0; unit = "m"
        except Exception:
            pass
    obs = {
        "resourceType":"Observation","status":"final",
        "category":[{"coding":[{"system":"http://terminology.hl7.org/CodeSystem/observation-category","code":"vital-signs"}]}],
        "code":{"coding":[{"system":"http://loinc.org","code":code,"display":display}],"text":display},
        "subject":{"reference":subject_ref},
        "effectiveDateTime": eff
    }
    if kind == "Quantity":
        q = mk_quantity(value, unit)
        if not q: return None
        obs["valueQuantity"] = q
    elif kind == "Integer":
        ival = mk_integer(value)
        if ival is None: return None
        obs["valueInteger"] = ival
    return obs

def main():
    if len(sys.argv) < 3:
        print("Usage: parse_health.py <export.xml> <out.json> [--subject Patient/example]", file=sys.stderr)
        sys.exit(2)
    export_path, out_path = sys.argv[1], sys.argv[2]
    subject = "Patient/example"
    if len(sys.argv) >= 4 and sys.argv[3].startswith("--subject="):
        subject = sys.argv[3].split("=",1)[1] or subject

    root = ET.parse(export_path).getroot()
    recs = root.findall(".//Record")
    entries = []
    made = skipped = 0

    bp = {}
    for r in recs:
        t = r.get("type")
        if t in ("HKQuantityTypeIdentifierBloodPressureSystolic","HKQuantityTypeIdentifierBloodPressureDiastolic"):
            key = (r.get("startDate"), r.get("endDate"))
            bp.setdefault(key, {})[t] = r
            continue
        o = obs_from_record(r, subject)
        if o is not None:
            rid = f"urn:uuid:{uuid.uuid4()}"
            entries.append({"request":{"method":"PUT","url":f"Observation/{rid}"},"fullUrl":rid,"resource":o})
            made += 1
        else:
            skipped += 1

    def bp_q(r):
        try: v = float(r.get("value"))
        except Exception: return None
        unit = r.get("unit") or "mm[Hg]"
        return {"value": v, "unit": unit, "system":"http://unitsofmeasure.org", "code": unit}

    for (start,end), pair in bp.items():
        s = pair.get("HKQuantityTypeIdentifierBloodPressureSystolic")
        d = pair.get("HKQuantityTypeIdentifierBloodPressureDiastolic")
        if s is not None and d is not None:
            eff = parse_datetime(end or start)
            comp_s = bp_q(s); comp_d = bp_q(d)
            if comp_s is None or comp_d is None:
                continue
            o = {
                "resourceType":"Observation","status":"final",
                "category":[{"coding":[{"system":"http://terminology.hl7.org/CodeSystem/observation-category","code":"vital-signs"}]}],
                "code":{"coding":[{"system":"http://loinc.org","code":"85354-9","display":"Blood pressure panel"}],"text":"Blood pressure"},
                "subject":{"reference":subject},"effectiveDateTime": eff,
                "component":[
                    {"code":{"coding":[{"system":"http://loinc.org","code":"8480-6","display":"Systolic"}]},"valueQuantity":comp_s},
                    {"code":{"coding":[{"system":"http://loinc.org","code":"8462-4","display":"Diastolic"}]},"valueQuantity":comp_d}
                ]
            }
            rid = f"urn:uuid:{uuid.uuid4()}"
            entries.append({"request":{"method":"PUT","url":f"Observation/{rid}"},"fullUrl":rid,"resource":o})
            made += 1
        else:
            for r in (s, d):
                if r is not None:
                    o = obs_from_record(r, subject)
                    if o is not None:
                        rid = f"urn:uuid:{uuid.uuid4()}"
                        entries.append({"request":{"method":"PUT","url":f"Observation/{rid}"},"fullUrl":rid,"resource":o})
                        made += 1

    bundle = {"resourceType":"Bundle","type":"transaction","entry":entries}
    with open(out_path,"w",encoding="utf-8") as f:
        json.dump(bundle, f, indent=2)
    print(json.dumps({"made":made,"skipped":skipped,"entries":len(entries)}, indent=2))

if __name__ == "__main__":
    main()
