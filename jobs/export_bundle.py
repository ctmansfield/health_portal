#!/usr/bin/env python3
import argparse, os, csv, json, zipfile, datetime as dt
from io import StringIO
from hp_etl.db import pg, dsn_from_env


def fetch_events(dsn):
    with pg(dsn) as conn, conn.cursor() as cur:
        cur.execute(
            """
          SELECT person_id, source, kind, code_system, code, value_num, unit, effective_time, meta
          FROM analytics.data_events
          ORDER BY effective_time
        """
        )
        cols = [d.name for d in cur.description]
        return cols, cur.fetchall()


def fetch_findings(dsn):
    with pg(dsn) as conn, conn.cursor() as cur:
        cur.execute(
            """
          SELECT person_id, finding_time, metric, method, score, level, "window", context
          FROM analytics.ai_findings
          ORDER BY finding_time
        """
        )
        cols = [d.name for d in cur.description]
        return cols, cur.fetchall()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dsn", default=dsn_from_env())
    ap.add_argument("--outdir", default="/mnt/nas_storage/exports")
    ap.add_argument("--pdf", default=None, help="optional path to include in the zip")
    ap.add_argument("--note", default="export bundle")
    args = ap.parse_args()

    os.makedirs(args.outdir, exist_ok=True)
    ts = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    outzip = os.path.join(args.outdir, f"health_bundle_{ts}.zip")

    with zipfile.ZipFile(outzip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        # CSV: events
        ecols, erows = fetch_events(args.dsn)
        sio = StringIO()
        w = csv.writer(sio)
        w.writerow(ecols)
        w.writerows(erows)
        zf.writestr("events.csv", sio.getvalue())

        # CSV: findings
        fcols, frows = fetch_findings(args.dsn)
        sio = StringIO()
        w = csv.writer(sio)
        w.writerow(fcols)
        w.writerows(frows)
        zf.writestr("findings.csv", sio.getvalue())

        # manifest.json
        manifest = {
            "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "note": args.note,
            "counts": {"events": len(erows), "findings": len(frows)},
        }
        zf.writestr("manifest.json", json.dumps(manifest, indent=2))

        # optional PDF
        if args.pdf and os.path.exists(args.pdf):
            zf.write(args.pdf, arcname=os.path.basename(args.pdf))

    print(outzip)


if __name__ == "__main__":
    main()
