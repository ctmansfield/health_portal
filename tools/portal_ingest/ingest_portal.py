
#!/usr/bin/env python3
"""
Parse a patient portal text export or a cleaned CSV, stage rows into ingest_portal.stg_portal_labs,
and merge mapped rows into analytics.data_events.

- Early de-dup within the run (by src_hash + natural key)
- Reject non-numeric values (logs to ingest_portal.rejections and rejections.csv)
- Map tests to LOINC using mappings/loinc_map.csv (exact/substring match, case-insensitive)
- Preserve provider, source filename, page/line order, and import timestamps in meta
"""
import argparse, csv, hashlib, json, os, re, sys, uuid, pytz
from datetime import datetime
from dateutil import parser as dtparser, tz as dateutil_tz
import psycopg2
from psycopg2.extras import execute_values

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
MAP_PATH = os.path.join(THIS_DIR, "mappings", "loinc_map.csv")

MONTHS = {
    'jan':1, 'feb':2, 'mar':3, 'apr':4, 'may':5, 'jun':6, 'jul':7, 'aug':8, 'sep':9, 'sept':9, 'oct':10, 'nov':11, 'dec':12
}

def load_loinc_map(path: str):
    mapping = []
    if not os.path.exists(path):
        return mapping
    with open(path, newline='') as f:
        r = csv.DictReader(f)
        for row in r:
            pat = row.get('pattern','').strip().upper()
            if not pat: 
                continue
            mapping.append({
                'pattern': pat,
                'loinc_code': row.get('loinc_code','').strip(),
                'canonical_name': row.get('canonical_name','').strip(),
                'unit_hint': row.get('unit_hint','').strip(),
                'notes': row.get('notes','').strip()
            })
    return mapping

def normalize_test_name(name: str) -> str:
    s = re.sub(r'\s+', ' ', name).strip().upper()
    s = s.replace('’', "'").replace('“','"').replace('”','"')
    s = s.replace('TOTAL BILIRUBIN', 'BILIRUBIN, TOTAL')
    s = s.replace('DIRECT BILIRUBIN', 'BILIRUBIN, DIRECT')
    return s

def map_loinc(test_name: str, mapping):
    n = normalize_test_name(test_name)
    # exact first
    for m in mapping:
        if n == m['pattern']:
            return m['loinc_code'], m
    # contains
    for m in mapping:
        if m['pattern'] and m['pattern'] in n:
            return m['loinc_code'], m
    return None, None

def parse_number_and_unit(val: str):
    if val is None:
        return None, None
    s = str(val).strip()
    if s.upper().startswith("SEE NOTE"):
        return None, None
    # strip "(calc)" and similar
    s = re.sub(r'\(.*?\)', '', s).strip()
    # split "119.0 mg/dL" or "230.0 Thousand/uL"
    m = re.match(r'^([+-]?\d+(?:\.\d+)?)\s*([A-Za-z/µ%0-9\.\-\^\(\)]*)$', s)
    if not m:
        # Could be percent like "31.9 %"
        m = re.match(r'^([+-]?\d+(?:\.\d+)?)\s*%$', s)
        if m:
            return float(m.group(1)), '%'
        return None, None
    val = float(m.group(1))
    unit = m.group(2).strip() or None
    return val, unit

def parse_portal_text(lines, default_tz):
    """
    Very simple state machine:
    - find blocks like: "<Mon> <DD>, <YYYY>          <Provider>"
    - subsequent rows until blank/next date block are test rows with columns
    """
    results = []
    cur_date = None
    cur_provider = None
    page = 1
    order = 0

    # pre-clean noise lines
    skip_re = re.compile(r'^(Continued on Page|Continued from Page|Health\s+Page|This summary|Date of Birth|Chad T\.)', re.I)

    date_line_re = re.compile(r'^\s*([A-Za-z]{3,9})\s+(\d{1,2}),\s*(\d{4})\s+(.+?)\s*$')
    # Table header sometimes shows "TEST" or fancy unicode; accept everything after the date line
    for raw in lines:
        line = raw.rstrip('\n')
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
            cur_date = datetime(int(y), MONTHS[mkey], int(d), 0, 0, 0, tzinfo=default_tz)
            cur_provider = provider.strip()
            order = 0
            continue

        if not cur_date or not cur_provider:
            continue

        # Likely a row with "TEST  CURRENT ..." -> split generously
        parts = re.split(r'\s{2,}', line.strip())
        if len(parts) < 2:
            continue
        test = parts[0].strip()
        val = parts[1].strip()
        ref = parts[2].strip() if len(parts) >= 3 else None
        flag = parts[3].strip() if len(parts) >= 4 else None

        results.append({
            'provider': cur_provider,
            'test_name': test,
            'value_text': val,
            'reference_text': ref,
            'flag': flag,
            'effective_time': cur_date,
            'src_line': line,
            'src_page': page,
            'src_order': order
        })
        order += 1

    return results

def parse_csv_rows(path, default_tz):
    rows = []
    with open(path, newline='') as f:
        r = csv.DictReader(f)
        headers = [h.strip() for h in r.fieldnames]
        # Heuristic header mapping
        def get(row, keys, default=None):
            for k in keys:
                if k in row and row[k]:
                    return row[k]
            return default
        for row in r:
            test = get(row, ['TEST','Test','test','name','Name'], '').strip()
            if not test:
                continue
            val  = get(row, ['CURRENT','Value','value','Result','RESULT'], '').strip()
            ref  = get(row, ['REFERENCE','Reference','Ref','ref'], None)
            flag = get(row, ['FLAG','Flag'], None)
            provider = get(row, ['PROVIDER','Provider'], None)
            dtxt = get(row, ['DATE','Date','date','Collected','COLLECTED'], None)
            etime = None
            if dtxt:
                try:
                    etime = dtparser.parse(dtxt)
                    if etime.tzinfo is None:
                        etime = default_tz.localize(etime)
                except Exception:
                    etime = None
            rows.append({
                'provider': provider,
                'test_name': test,
                'value_text': val,
                'reference_text': ref,
                'flag': flag,
                'effective_time': etime,
                'src_line': json.dumps(row, ensure_ascii=False),
                'src_page': None,
                'src_order': None
            })
    return rows

def connect(dsn):
    return psycopg2.connect(dsn)

def ensure_run(conn, run_id, source_file, person_id):
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO ingest_portal.import_run (run_id, source_file, person_id, importer_version)
            VALUES (%s,%s,%s,%s)
            ON CONFLICT (run_id) DO NOTHING
        """, (run_id, source_file, person_id, "portal_ingest_v1"))
    conn.commit()

def stage_rows(conn, rows):
    # bulk insert to staging
    cols = ["run_id","person_id","provider","test_name","value_num","unit","flag","reference_text",
            "effective_time","code_system","code","src_line","src_page","src_order","src_hash","meta"]
    values = [[
        r['run_id'], r['person_id'], r['provider'], r['test_name'], r['value_num'], r['unit'], r['flag'], r['reference_text'],
        r['effective_time'], r['code_system'], r['code'], r['src_line'], r['src_page'], r['src_order'], r['src_hash'], json.dumps(r['meta'])
    ] for r in rows]
    with conn.cursor() as cur:
        execute_values(cur, f"INSERT INTO ingest_portal.stg_portal_labs ({','.join(cols)}) VALUES %s", values, page_size=1000)
    conn.commit()

def insert_rejections(conn, run_id, rejections):
    if not rejections:
        return
    cols = ["run_id","reason","provider","raw_text","parsed","effective_time"]
    values = [[run_id, r['reason'], r.get('provider'), r.get('raw_text'), json.dumps(r.get('parsed') or {}), r.get('effective_time')] for r in rejections]
    with conn.cursor() as cur:
        execute_values(cur, f"INSERT INTO ingest_portal.rejections ({','.join(cols)}) VALUES %s", values, page_size=1000)
    conn.commit()

def insert_dups(conn, run_id, dups):
    if not dups:
        return
    cols = ["run_id","src_hash","reason","details"]
    values = [[run_id, d['src_hash'], d['reason'], json.dumps(d.get('details') or {})] for d in dups]
    with conn.cursor() as cur:
        execute_values(cur, f"INSERT INTO ingest_portal.dup_log ({','.join(cols)}) VALUES %s", values, page_size=1000)
    conn.commit()

def compute_src_hash(d: dict) -> str:
    key = f"{d.get('provider','')}\x1F{normalize_test_name(d.get('test_name',''))}\x1F{d.get('value_text','')}\x1F{d.get('effective_time')}\x1F{d.get('src_line','')}"
    return hashlib.sha256(key.encode('utf-8')).hexdigest()

def natural_key(d: dict):
    return (
        normalize_test_name(d.get('test_name','')),
        d.get('value_num'),
        (d.get('unit') or '').strip(),
        d.get('effective_time'),
        d.get('provider')
    )

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dsn", default=os.getenv("HP_PG_DSN"), help="Postgres DSN; or set HP_PG_DSN")
    ap.add_argument("--person-id", required=True, help="Target person_id for analytics.data_events")
    ap.add_argument("--input", required=True, nargs="+", help="Input path(s): CSV or text")
    ap.add_argument("--source-file", required=True, help="Source file label to store in meta")
    ap.add_argument("--tz", default="America/New_York", help="Timezone of dates in the portal export")
    ap.add_argument("--dry-run", action="store_true", help="Parse and write CSV logs only; do not touch DB")
    ap.add_argument("--stage-only", action="store_true", help="Stage into ingest_portal.* tables but DO NOT merge into analytics.data_events")
    args = ap.parse_args()

    if not args.dsn and not args.dry_run:
        print("ERROR: --dsn or HP_PG_DSN required (unless --dry-run).", file=sys.stderr)
        sys.exit(2)

    tz = pytz.timezone(args.tz)
    mapping = load_loinc_map(MAP_PATH)
    run_id = uuid.uuid4()

    outdir = os.path.join(os.getcwd(), "portal_ingest_out", str(run_id))
    os.makedirs(outdir, exist_ok=True)

    all_rows = []
    rejects = []
    dedup_keys = set()
    dups = []

    for path in args.input:
        if not os.path.exists(path):
            print(f"[warn] missing input {path}", file=sys.stderr)
            continue

        ext = os.path.splitext(path)[1].lower()
        if ext in (".csv", ".tsv"):
            rows = parse_csv_rows(path, tz)
        else:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                rows = parse_portal_text(f.readlines(), tz)

        for r in rows:
            r['person_id'] = args.person_id
            r['run_id'] = str(run_id)
            r['meta'] = {
                "source_file": args.source_file,
                "imported_at": datetime.now(tz).isoformat(),
            }
            # parse numeric
            val_num, unit = parse_number_and_unit(r['value_text'])
            if val_num is None:
                rejects.append({
                    "reason": "non-numeric or SEE NOTE",
                    "provider": r.get('provider'),
                    "raw_text": r.get('src_line'),
                    "parsed": {"test": r.get('test_name'), "value": r.get('value_text'), "ref": r.get('reference_text')},
                    "effective_time": r.get('effective_time')
                })
                continue

            r['value_num'] = val_num
            r['unit'] = unit
            # map loinc
            code, meta = map_loinc(r['test_name'], mapping)
            if code:
                r['code_system'] = 'LOINC'
                r['code'] = code
                if meta and meta.get('unit_hint') and not r['unit']:
                    r['unit'] = meta['unit_hint']
            else:
                r['code_system'] = 'LOCAL'
                r['code'] = normalize_test_name(r['test_name'])

            # default provider/etime
            if not r.get('effective_time'):
                # fallback: use today at 00:00
                r['effective_time'] = tz.localize(datetime.now().replace(hour=0, minute=0, second=0, microsecond=0))
            if not r.get('provider'):
                r['provider'] = 'Unknown'

            # hashes + dedupe
            r['src_hash'] = compute_src_hash(r)
            nk = natural_key(r)
            if nk in dedup_keys:
                dups.append({"src_hash": r['src_hash'], "reason": "within-run duplicate", "details": {"test": r['test_name'], "value": r['value_num'], "unit": r['unit']}})
                continue
            dedup_keys.add(nk)
            all_rows.append(r)

    # Write CSV logs
    staged_csv = os.path.join(outdir, "staged.csv")
    dup_csv = os.path.join(outdir, "duplicates.csv")
    rej_csv = os.path.join(outdir, "rejections.csv")
    fields = ["run_id","person_id","provider","test_name","value_num","unit","flag","reference_text","effective_time","code_system","code","src_line","src_page","src_order","src_hash"]
    with open(staged_csv, "w", newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in all_rows:
            w.writerow({k: r.get(k) for k in fields})

    with open(dup_csv, "w", newline='') as f:
    w = csv.DictWriter(f, fieldnames=["run_id","src_hash","reason","details"])
    w.writeheader()
    for d in dups:
        row = {"run_id": str(run_id), **d}
        w.writerow(row)

    with open(rej_csv, "w", newline='') as f:
    w = csv.DictWriter(f, fieldnames=["run_id","reason","provider","raw_text","effective_time","parsed"])
    w.writeheader()
    for rj in rejects:
        row = {"run_id": str(run_id), **rj}
        w.writerow(row)

    summary = {
        "run_id": str(run_id),
        "inputs": args.input,
        "staged_rows": len(all_rows),
        "duplicates": len(dups),
        "rejections": len(rejects)
    }
    with open(os.path.join(outdir, "summary.json"), "w") as f:
        json.dump(summary, f, indent=2, default=str)

    if args.dry_run:
        print(json.dumps(summary, indent=2))
        print(f"[dry-run] wrote logs to {outdir}")
        return

    # DB work
    conn = connect(args.dsn)
    try:
        ensure_run(conn, str(run_id), args.source_file, args.person_id)
        if all_rows:
            stage_rows(conn, all_rows)
        insert_rejections(conn, str(run_id), rejects)
        insert_dups(conn, str(run_id), dups)

        if args.stage_only:
            print(f"[stage-only] staged rows in ingest_portal.stg_portal_labs for run_id={run_id}")
            return

        # Merge into analytics (default behavior)
        with conn.cursor() as cur:
            cur.execute("SET search_path TO public;")
        conn.commit()

        merge_sql = open(os.path.join(os.path.dirname(THIS_DIR), "..", "services", "healthdb-pg-0001", "init", "057_portal_ingest_merge.sql")).read()
        merge_sql_exe = merge_sql.replace(":'run_id'", "%s")
        with conn.cursor() as cur:
            cur.execute(merge_sql_exe, (str(run_id),))
        conn.commit()

    finally:
        conn.close()

    print(json.dumps(summary, indent=2))
    print(f"[ok] wrote logs to {outdir}")

if __name__ == "__main__":
    main()
