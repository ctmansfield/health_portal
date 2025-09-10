#!/usr/bin/env python3
import argparse, os, csv, zipfile, datetime as dt
from io import StringIO
from hp_etl.db import pg, dsn_from_env

EXPORT_DIR = "/mnt/nas_storage/exports"


def fetch(dsn, sql):
    with pg(dsn) as conn, conn.cursor() as cur:
        cur.execute(sql)
        cols = [d.name for d in cur.description]
        rows = cur.fetchall()
    return cols, rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dsn", default=dsn_from_env())
    ap.add_argument("--outdir", default=EXPORT_DIR)
    ap.add_argument("--pdf", default=None)
    args = ap.parse_args()

    os.makedirs(args.outdir, exist_ok=True)
    ts = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    outzip = os.path.join(args.outdir, f"health_bundle_{ts}.zip")

    with zipfile.ZipFile(outzip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        ecols, erows = fetch(
            args.dsn,
            """
            SELECT person_id, source, kind, code_system, code, value_num, unit, effective_time, meta
            FROM analytics.data_events ORDER BY effective_time;
        """,
        )
        sio = StringIO()
        w = csv.writer(sio)
        w.writerow(ecols)
        w.writerows(erows)
        zf.writestr("events.csv", sio.getvalue())

        try:
            fcols, frows = fetch(
                args.dsn,
                """
                SELECT person_id, finding_time, metric, method, score, level, "window", context
                FROM analytics.ai_findings ORDER BY finding_time;
            """,
            )
            sio = StringIO()
            w = csv.writer(sio)
            w.writerow(fcols)
            w.writerows(frows)
            zf.writestr("findings.csv", sio.getvalue())
        except Exception:
            pass

        if args.pdf and os.path.exists(args.pdf):
            zf.write(args.pdf, arcname=os.path.basename(args.pdf))

    print(outzip)


if __name__ == "__main__":
    main()
