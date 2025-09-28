#!/usr/bin/env python3
import os, sys, json, argparse, hashlib, uuid
from datetime import datetime
import psycopg2
from psycopg2 import sql

ROOT = os.path.dirname(__file__)
DDL_FILE = os.path.join(ROOT, "sql", "create_tables.sql")

def use_schema(cur, schema):
    if schema:
        cur.execute(sql.SQL("create schema if not exists {}").format(sql.Identifier(schema)))
        cur.execute(sql.SQL("set search_path to {}, public").format(sql.Identifier(schema)))

def load_ddl(cur):
    with open(DDL_FILE,"r",encoding="utf-8") as f:
        cur.execute(f.read())

def connect(dsn): return psycopg2.connect(dsn, application_name="warehouse_ingest_files_v3")

def to_ts(s):
    if not s: return None
    try: return datetime.fromisoformat(s.replace("Z","+00:00"))
    except Exception: return None

def subject_ref(r):   return (r.get("subject") or r.get("patient") or {}).get("reference")
def encounter_ref(r): return (r.get("encounter") or {}).get("reference")
def eff_time(r):
    return (r.get("effectiveDateTime")
            or (r.get("effectivePeriod") or {}).get("start")
            or r.get("issued") or r.get("authoredOn") or r.get("occurrenceDateTime"))

def json_codes(r):
    out=[]; code=r.get("code") or {}
    for cc in code.get("coding",[]) or []:
        if isinstance(cc,dict):
            out.append({"system":cc.get("system"),"code":cc.get("code"),"display":cc.get("display")})
    cat=r.get("category") or []
    if isinstance(cat,list) and cat and cat[0].get("coding"):
        for cc in cat[0]["coding"]:
            if isinstance(cc,dict):
                out.append({"system":cc.get("system"),"code":cc.get("code"),"display":cc.get("display")})
    return out or None

def deterministic_uuid(base, rt, rid):
    name = f"{base.rstrip('/')}/{rt}/{rid}"
    return uuid.uuid5(uuid.NAMESPACE_URL, name)

def ensure_ref(cur, base, rt, rid):
    ref_uid = deterministic_uuid(base, rt, rid)
    cur.execute("""
        insert into ref_map(ref_uid, server_base, resource_type, fhir_id)
        values (%s,%s,%s,%s)
        on conflict (server_base,resource_type,fhir_id) do nothing
    """, (str(ref_uid), base, rt, rid))
    cur.execute("""select ref_uid from ref_map where server_base=%s and resource_type=%s and fhir_id=%s""",
                (base, rt, rid))
    return cur.fetchone()[0]

def upsert_raw(cur, ref_uid, rt, res, label):
    meta = res.get("meta", {})
    version = meta.get("versionId") or "0"
    cur.execute("""
        insert into fhir_resource(ref_uid,version_id,last_updated,patient_ref,encounter_ref,
                                  resource_type,effective_at,status,codes,source_label,resource_json)
        values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        on conflict (ref_uid,version_id) do nothing
    """, (
        ref_uid, version, to_ts(meta.get("lastUpdated")),
        subject_ref(res), encounter_ref(res), rt, to_ts(eff_time(res)),
        res.get("status"), json.dumps(json_codes(res)) if json_codes(res) else None, label, json.dumps(res)
    ))

def upsert_obs(cur, ref_uid, r):
    c=r.get("code") or {}; system=code=display=None
    if c.get("coding"):
        cc=c["coding"][0]; system,code,display = cc.get("system"),cc.get("code"),cc.get("display")
    name = display or c.get("text"); category=None
    cat=r.get("category") or []
    if isinstance(cat,list) and cat and cat[0].get("coding"):
        category = cat[0]["coding"][0].get("code")
    val_num=val_unit=val_str=None
    if "valueQuantity" in r:
        vq=r["valueQuantity"]; val_num=vq.get("value"); val_unit=vq.get("unit") or vq.get("code")
    elif "valueString" in r: val_str=r.get("valueString")
    cur.execute("""
        insert into obs_rollup(ref_uid,fhir_id,patient_ref,code_system,code,name,category,
                               issued_at,effective_at,val_num,val_unit,val_str,components,ref_range)
        values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        on conflict (ref_uid) do update set
          patient_ref=excluded.patient_ref, code_system=excluded.code_system, code=excluded.code,
          name=excluded.name, category=excluded.category, issued_at=excluded.issued_at,
          effective_at=excluded.effective_at, val_num=excluded.val_num, val_unit=excluded.val_unit,
          val_str=excluded.val_str, components=excluded.components, ref_range=excluded.ref_range
    """, (
        ref_uid, r.get("id"), subject_ref(r), system, code, name, category,
        to_ts(r.get("issued")), to_ts(eff_time(r)),
        val_num, val_unit, val_str,
        json.dumps(r.get("component")) if r.get("component") else None,
        json.dumps(r.get("referenceRange")) if r.get("referenceRange") else None
    ))

def upsert_med(cur, ref_uid, r):
    med_text = ((r.get("medicationCodeableConcept") or {}).get("text"))
    rx_system=rx_code=None
    mcc=r.get("medicationCodeableConcept") or {}
    if mcc.get("coding"):
        cc=mcc["coding"][0]; rx_system, rx_code = cc.get("system"), cc.get("code")
    note=None
    if r.get("note"): note=" | ".join([n.get("text","") for n in r["note"] if n.get("text")])
    start=(r.get("effectivePeriod") or {}).get("start") or r.get("effectiveDateTime")
    end=(r.get("effectivePeriod") or {}).get("end")
    cur.execute("""
        insert into med_stmt_rollup(ref_uid,fhir_id,patient_ref,rx_system,rx_code,med_text,status,
                                    start_time,end_time,last_filled,note,info_source)
        values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        on conflict (ref_uid) do update set
          patient_ref=excluded.patient_ref, rx_system=excluded.rx_system, rx_code=excluded.rx_code,
          med_text=excluded.med_text, status=excluded.status, start_time=excluded.start_time,
          end_time=excluded.end_time, last_filled=excluded.last_filled, note=excluded.note, info_source=excluded.info_source
    """, (
        ref_uid, r.get("id"), subject_ref(r),
        rx_system, rx_code, med_text, r.get("status"),
        to_ts(start), to_ts(end), to_ts(r.get("dateAsserted")), note,
        (r.get("informationSource") or {}).get("reference")
    ))

def upsert_condition(cur, ref_uid, r):
    system=code=display=None
    c=r.get("code") or {}
    if c.get("coding"):
        cc=c["coding"][0]; system,code,display = cc.get("system"), cc.get("code"), cc.get("display")
    clin=(r.get("clinicalStatus") or {}).get("coding",[{}])[0].get("code")
    ver =(r.get("verificationStatus") or {}).get("coding",[{}])[0].get("code")
    onset=r.get("onsetDateTime") or (r.get("onsetPeriod") or {}).get("start")
    abate=r.get("abatementDateTime") or (r.get("abatementPeriod") or {}).get("end")
    cur.execute("""
        insert into condition_rollup(ref_uid,fhir_id,patient_ref,code_system,code,display,
                                     clinical_status,verification,onset_at,abatement_at)
        values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        on conflict (ref_uid) do update set
          patient_ref=excluded.patient_ref, code_system=excluded.code_system, code=excluded.code,
          display=excluded.display, clinical_status=excluded.clinical_status, verification=excluded.verification,
          onset_at=excluded.onset_at, abatement_at=excluded.abatement_at
    """, (
        ref_uid, r.get("id"), subject_ref(r), system, code, display, clin, ver,
        to_ts(onset), to_ts(abate)
    ))

def synth_id(rt,res):
    return f"{rt.lower()}-{hashlib.sha1(json.dumps(res,sort_keys=True).encode()).hexdigest()[:12]}"

def ensure_id(rt,res):
    if not res.get("id"): res["id"] = synth_id(rt,res)

def process(cur, base, label, res, kinds):
    if not isinstance(res,dict) or "resourceType" not in res: return
    rt=res["resourceType"]; ensure_id(rt,res)
    ref_uid = ensure_ref(cur, base, rt, res["id"])
    upsert_raw(cur, ref_uid, rt, res, label)
    if rt=="Observation" and "Observation" in kinds:                   upsert_obs(cur, ref_uid, res)
    elif rt=="MedicationStatement" and "MedicationStatement" in kinds: upsert_med(cur, ref_uid, res)
    elif rt=="Condition" and "Condition" in kinds:                     upsert_condition(cur, ref_uid, res)

def iter_file(path):
    if path.lower().endswith(".ndjson"):
        try:
            with open(path,"r",encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line: continue
                    try:
                        yield json.loads(line)
                    except Exception as e:
                        print(f"[WARN] Skipping bad NDJSON line in {path}: {e}", file=sys.stderr)
        except Exception as e:
            print(f"[WARN] Skipping file (cannot open NDJSON): {path} :: {e}", file=sys.stderr)
        return
    # JSON files
    try:
        with open(path,"r",encoding="utf-8") as f:
            doc = json.load(f)
    except Exception as e:
        print(f"[WARN] Skipping file (parse error): {path} :: {e}", file=sys.stderr)
        return
    if isinstance(doc,dict) and doc.get("resourceType")=="Bundle" and isinstance(doc.get("entry"),list):
        for e in doc["entry"]:
            if isinstance(e,dict) and "resource" in e: yield e["resource"]
    elif isinstance(doc,list):
        for r in doc: yield r
    else:
        yield doc

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--dsn", required=True)
    ap.add_argument("--schema")
    ap.add_argument("--server-base", default="file:///local")
    ap.add_argument("--source-label", default="file_import")
    ap.add_argument("--kinds", nargs="+", default=["Observation","MedicationStatement","Condition"])
    ap.add_argument("--files", nargs="+", required=True)
    args=ap.parse_args()

    with connect(args.dsn) as cx:
        with cx.cursor() as cur:
            use_schema(cur, args.schema); load_ddl(cur); cx.commit()

    totals={"resources":0,"by_type":{}}
    with connect(args.dsn) as cx:
        with cx.cursor() as cur:
            use_schema(cur, args.schema)
            for p in args.files:
                if not os.path.exists(p): 
                    # ignore non-matching globs
                    continue
                for r in iter_file(p):
                    process(cur, args.server_base, args.source_label, r, set(args.kinds))
                    totals["resources"] += 1
                    rt = r.get("resourceType","?")
                    totals["by_type"][rt] = totals["by_type"].get(rt,0)+1
                cx.commit()
    print(json.dumps(totals, indent=2))

if __name__=="__main__": main()
