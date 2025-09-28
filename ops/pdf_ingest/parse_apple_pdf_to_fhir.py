#!/usr/bin/env python3
import re, json, argparse
from datetime import datetime
UNITS=r"(?:mg/dL|mmol/L|%|U/L|IU/L|ng/mL|pg/mL|g/dL|µIU/mL|mIU/mL|x10\^3/µL|10\^3/µL|10\^9/L)"
DATE_RX=r"\b(?:\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{2,4}|[A-Za-z]{3,9}\s+\d{1,2},\s*\d{4})\b"
VAL=re.compile(rf"(?P<name>[A-Za-z0-9 \-/()+%]+?)\s*[:\-]?\s*(?P<value>[-+]?\d+(?:\.\d+)?)\s*(?P<unit>{UNITS})\b")
MED=re.compile(r"^(?P<name>[A-Z][A-Za-z0-9' -]{2,})\s+(?P<strength>\d+(?:\.\d+)?)\s*(?P<u>mg|mcg|g|mL|%)",re.I)
def iso(d):
  for fmt in ("%Y-%m-%d","%m/%d/%Y","%m/%d/%y","%B %d, %Y","%b %d, %Y"):
    try: return datetime.strptime(d,fmt).isoformat()
    except: pass
  return None
ap=argparse.ArgumentParser()
ap.add_argument("--text",required=True); ap.add_argument("--out",required=True); ap.add_argument("--subject",default="Patient/example")
a=ap.parse_args()
obs=[]; meds=[]; last=None
for raw in open(a.text,"r",encoding="utf-8",errors="ignore"):
  line=" ".join(raw.strip().split()); 
  if not line: continue
  m=re.search(DATE_RX,line); 
  if m: last=iso(m.group(0))
  m=VAL.search(line)
  if m:
    name=m.group("name").strip(" :-"); val=float(m.group("value")); unit=m.group("unit")
    obs.append({"resourceType":"Observation","status":"final","code":{"text":name},"subject":{"reference":a.subject},
                "effectiveDateTime":last,"valueQuantity":{"value":val,"unit":unit}}); continue
  m=MED.match(line)
  if m:
    meds.append({"resourceType":"MedicationStatement","status":"active",
                "medicationCodeableConcept":{"text":f"{m.group('name')} {m.group('strength')}{m.group('u')}"},
                "subject":{"reference":a.subject},"effectiveDateTime":last,"note":[{"text":line}]})
bundle={"resourceType":"Bundle","type":"transaction","entry":[{"resource":r,"request":{"method":"POST","url":r["resourceType"]}} for r in (obs+meds)]}
open(a.out,"w",encoding="utf-8").write(json.dumps(bundle,indent=2))
print(json.dumps({"labs":len(obs),"medications":len(meds),"entries":len(bundle["entry"])},indent=2))
