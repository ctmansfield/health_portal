#!/usr/bin/env python3
"""
Export FHIR R4 -> CSVs (Observations + MedicationStatements) for a given subject.

Usage:
  export_fhir.py --base http://localhost:8085/fhir \
                 --subject Patient/example \
                 --labs-out /tmp/labs.csv \
                 --meds-out /tmp/meds.csv
Options:
  --obs-category laboratory      # optional filter; otherwise exports all Observations for subject
"""
import sys, json, csv, urllib.parse, urllib.request, argparse

def http_get_json(url, headers=None):
    req = urllib.request.Request(url, headers=headers or {"Accept":"application/fhir+json"})
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))

def fetch_all(base, resource_type, params):
    params = dict(params or {})
    if "_count" not in params:
        params["_count"] = 200
    url = base.rstrip("/") + "/" + resource_type + "?" + urllib.parse.urlencode(params)
    out = []
    while True:
        bundle = http_get_json(url)
        for e in bundle.get("entry", []):
            res = e.get("resource")
            if res and res.get("resourceType") == resource_type:
                out.append(res)
        next_url = None
        for l in bundle.get("link", []):
            if l.get("relation") == "next":
                next_url = l.get("url")
                break
        if not next_url:
            break
        url = next_url
    return out

def first(x, path, default=None):
    cur = x
    for p in path:
        if isinstance(cur, dict):
            cur = cur.get(p)
        elif isinstance(cur, list) and isinstance(p, int):
            cur = cur[p] if p < len(cur) else None
        else:
            return default
        if cur is None:
            return default
    return cur

def obs_rows(obs, base):
    rows = []
    rid = obs.get("id")
    when = obs.get("effectiveDateTime") or first(obs, ["effectivePeriod","start"])
    code_text = first(obs, ["code","text"])
    loinc = first(obs, ["code","coding",0,"code"])
    display = first(obs, ["code","coding",0,"display"])
    name = display or code_text or loinc or ""
    src = f"{base.rstrip('/')}/Observation/{rid}" if rid else ""
    # single value
    if "valueQuantity" in obs:
        q = obs["valueQuantity"]; val = q.get("value"); unit = q.get("unit") or q.get("code") or ""
        rows.append([when, name, loinc or "", val, unit, "Observation", src])
    elif "valueString" in obs:
        rows.append([when, name, loinc or "", obs["valueString"], "", "Observation", src])
    # components (e.g., blood pressure)
    for comp in obs.get("component", []):
        c_code_text = first(comp, ["code","text"])
        c_loinc = first(comp, ["code","coding",0,"code"])
        c_disp = first(comp, ["code","coding",0,"display"])
        c_name = c_disp or c_code_text or c_loinc or name
        if "valueQuantity" in comp:
            q = comp["valueQuantity"]; val = q.get("value"); unit = q.get("unit") or q.get("code") or ""
            rows.append([when, c_name, c_loinc or "", val, unit, "Observation.component", src])
        elif "valueString" in comp:
            rows.append([when, c_name, c_loinc or "", comp["valueString"], "", "Observation.component", src])
    return rows

def med_rows(ms, base):
    rid = ms.get("id")
    when = ms.get("effectiveDateTime") or first(ms, ["effectivePeriod","start"])
    status = ms.get("status") or ""
    med_text = first(ms, ["medicationCodeableConcept","text"]) or ""
    note = " | ".join(n.get("text","") for n in ms.get("note",[]) if n.get("text")) if ms.get("note") else ""
    src = f"{base.rstrip('/')}/MedicationStatement/{rid}" if rid else ""
    return [[when, med_text, status, note, "MedicationStatement", src]]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True, help="FHIR base URL, e.g. http://localhost:8085/fhir")
    ap.add_argument("--subject", required=True, help="FHIR reference, e.g. Patient/example")
    ap.add_argument("--labs-out", required=True)
    ap.add_argument("--meds-out", required=True)
    ap.add_argument("--obs-category", default=None)
    args = ap.parse_args()

    # Observations
    obs_params = {"subject": args.subject}
    if args.obs_category:
        obs_params["category"] = args.obs_category
    observations = fetch_all(args.base, "Observation", obs_params)

    # MedicationStatements
    meds = fetch_all(args.base, "MedicationStatement", {"subject": args.subject})

    # Write CSVs
    with open(args.labs_out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["date", "name", "loinc", "value", "unit", "kind", "source"])
        for o in observations:
            for row in obs_rows(o, args.base):
                w.writerow(row)

    with open(args.meds_out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["date", "medication", "status", "note", "kind", "source"])
        for m in meds:
            for row in med_rows(m, args.base):
                w.writerow(row)

    print(json.dumps({
        "observations": len(observations),
        "medication_statements": len(meds),
        "labs_csv": args.labs_out,
        "meds_csv": args.meds_out
    }, indent=2))

if __name__ == "__main__":
    main()
