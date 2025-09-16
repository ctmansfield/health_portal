#!/usr/bin/env python3
"""
VA Blue Button TXT -> FHIR (R4) Bundle (labs + medications).

Usage:
  parse_va_blue_button.py <input.txt> <out.json> [--subject=Patient/example]
"""
import sys, json, re, uuid
from datetime import datetime

def parse_date(s):
    if not s: return None
    s = s.replace("a.m.", "AM").replace("p.m.", "PM").replace("a.m", "AM").replace("p.m", "PM")
    fmts = ["%B %d, %Y %I:%M %p","%B %d, %Y, %I:%M %p","%B %d, %Y"]
    for fmt in fmts:
        try: return datetime.strptime(s.strip(), fmt).isoformat()
        except Exception: pass
    return None

def section(text, header_regex, next_regex=None):
    m = re.search(header_regex, text, re.IGNORECASE)
    if not m: return ""
    start = m.end()
    if next_regex:
        n = re.search(next_regex, text[start:], re.IGNORECASE)
        end = start + (n.start() if n else 0)
    else:
        end = len(text)
    return text[start:end]

def extract_labs(text):
    sec = section(text, r"\n1\)\s*Lab and test results\b", r"\n2\)\s*")
    results = []
    for res_m in re.finditer(r"\nResult:\s*([^\n]+)", sec):
        sidx = sec.rfind("\n\n", 0, res_m.start()); sidx = 0 if sidx == -1 else sidx
        eidx = sec.find("\n\n", res_m.end());        eidx = len(sec) if eidx == -1 else eidx
        block = sec[sidx:eidx]

        name = None; when = None; unit = None; value = None; ref = None
        m_on = re.search(r"([A-Z0-9 \-/()+]+)\s+on\s+([A-Za-z]+\s+\d{1,2},\s+\d{4}(?:,?\s+\d{1,2}:\d{2}\s*(?:a\.m\.|p\.m\.|AM|PM))?)", block, re.IGNORECASE)
        if m_on:
            name = m_on.group(1).strip()
            when = parse_date(m_on.group(2))
        if not name:
            caps = re.findall(r"\n([A-Z0-9][A-Z0-9 \-/()+]{2,})\n", block)
            if caps: name = caps[0].strip()

        result_line = res_m.group(1).strip()
        m_val_unit = re.match(r"([<>]?\s*[\d\.]+)\s*([^\s].*)?$", result_line)
        if m_val_unit:
            value = m_val_unit.group(1).strip()
            unit = (m_val_unit.group(2) or "").strip() or None
        else:
            value = result_line; unit = None

        m_ref = re.search(r"Reference range:\s*([^\n]+)", block)
        if m_ref: ref = m_ref.group(1).strip()

        results.append({"name": name or "Unknown test","value": value,"unit": unit,"reference_range": ref,"when": when})
    return results

def extract_meds(text):
    m = re.search(r"\n\d+\)\s*Medications\b", text) or re.search(r"\nMedications\b", text)
    if not m: return []
    start = m.end()
    n = re.search(r"\n\d+\)\s*[A-Z]", text[start:])
    sec = text[start: start + (n.start() if n else 0)]

    entries = re.split(r"\nTitle:\s*", sec)[1:]
    meds = []
    for entry in entries:
        lines = entry.splitlines()
        name = (lines[0].strip() if lines else "Unknown").strip()

        last_filled = status = instructions = reason = quantity = None
        m1 = re.search(r"Last filled on:\s*(.+)", entry);  last_filled = parse_date(m1.group(1)) if m1 else None
        m2 = re.search(r"Status:\s*([a-zA-Z- ]+)", entry); status = m2.group(1).strip().lower() if m2 else None
        m3 = re.search(r"Instructions:\s*(.+)", entry);    instructions = m3.group(1).strip() if m3 else None
        m4 = re.search(r"Reason for use:\s*(.+)", entry);  reason = m4.group(1).strip() if m4 else None
        m5 = re.search(r"Quantity:\s*([^\n]+)", entry);    quantity = m5.group(1).strip() if m5 else None

        meds.append({"name": name,"last_filled": last_filled,"status": status,"instructions": instructions,"reason": reason,"quantity": quantity})
    return meds

def med_status_to_fhir(s):
    if not s: return "unknown"
    s = s.lower()
    if "active" in s: return "active"
    if "discontinue" in s or "stopped" in s: return "stopped"
    if "expired" in s: return "completed"
    if "hold" in s: return "on-hold"
    if "intended" in s: return "intended"
    return "unknown"

def main():
    if len(sys.argv) < 3:
        print("Usage: parse_va_blue_button.py <input.txt> <out.json> [--subject=Patient/example]", file=sys.stderr); sys.exit(2)
    in_path, out_path = sys.argv[1], sys.argv[2]
    subject = "Patient/example"
    if len(sys.argv) >= 4 and sys.argv[3].startswith("--subject="):
        subject = sys.argv[3].split("=",1)[1] or subject

    with open(in_path, "r", encoding="utf-8") as f: text = f.read()
    labs = extract_labs(text); meds = extract_meds(text)
    entries = []

    # Labs -> Observation (POST to collection)
    for lab in labs:
        obs = {"resourceType":"Observation","status":"final","code":{"text": lab["name"]},"subject":{"reference":subject}}
        if lab.get("when"): obs["effectiveDateTime"] = lab["when"]
        try:
            v = float(lab["value"].replace("<","").replace(">",""))
            q = {"value": v}
            if lab.get("unit"):
                q.update({"unit": lab["unit"], "system":"http://unitsofmeasure.org","code": lab["unit"]})
            obs["valueQuantity"] = q
        except Exception:
            obs["valueString"] = lab["value"]
        if lab.get("reference_range"):
            obs.setdefault("note", []).append({"text": f"Reference range: {lab['reference_range']}"})
        entries.append({
            "fullUrl": f"urn:uuid:{uuid.uuid4()}",
            "resource": obs,
            "request": {"method":"POST","url":"Observation"}
        })

    # Meds -> MedicationStatement (POST to collection)
    for med in meds:
        ms = {"resourceType":"MedicationStatement","status": med_status_to_fhir(med.get("status")),
              "medicationCodeableConcept":{"text": med["name"]},"subject":{"reference":subject}}
        if med.get("last_filled"): ms["effectiveDateTime"] = med["last_filled"]
        note_bits = []
        if med.get("instructions"): note_bits.append(f"Sig: {med['instructions']}")
        if med.get("reason"):       note_bits.append(f"Reason: {med['reason']}")
        if med.get("quantity"):     note_bits.append(f"Qty: {med['quantity']}")
        if note_bits: ms["note"] = [{"text": " | ".join(note_bits)}]
        entries.append({
            "fullUrl": f"urn:uuid:{uuid.uuid4()}",
            "resource": ms,
            "request": {"method":"POST","url":"MedicationStatement"}
        })

    bundle = {"resourceType":"Bundle","type":"transaction","entry": entries}
    with open(out_path, "w", encoding="utf-8") as f: json.dump(bundle, f, indent=2)
    print(json.dumps({"labs": len(labs), "medications": len(meds), "entries": len(entries)}, indent=2))

if __name__ == "__main__": main()
