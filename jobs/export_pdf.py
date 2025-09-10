#!/usr/bin/env python3
import argparse, os, datetime as dt
from hp_etl.db import pg, dsn_from_env

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors

EXPORT_DIR = "/mnt/nas_storage/exports"


def q1(dsn, sql, params=()):
    with pg(dsn) as conn, conn.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchone()


def qn(dsn, sql, params=()):
    with pg(dsn) as conn, conn.cursor() as cur:
        cur.execute(sql, params)
        cols = [d.name for d in cur.description]
        return cols, [dict(zip(cols, r)) for r in cur.fetchall()]


def build_pdf(dsn, outpath):
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("Health Report", styles["Title"]))
    story.append(
        Paragraph(dt.datetime.now().strftime("%Y-%m-%d %H:%M UTC"), styles["Normal"])
    )
    story.append(Spacer(1, 12))

    # Latest vitals (card)
    cols, vitals = qn(
        dsn,
        "SELECT person_id, hr_latest, spo2_latest, updated_at FROM analytics.v_vitals_latest ORDER BY person_id",
    )
    if vitals:
        data = [["Person", "HR (bpm)", "SpO2 (%)", "Updated"]]
        for r in vitals:
            data.append(
                [
                    r["person_id"],
                    f"{(r['hr_latest'] or 0):.0f}",
                    f"{(r['spo2_latest'] or 0)*100:.0f}",
                    str(r["updated_at"]),
                ]
            )
        t = Table(data, hAlign="LEFT")
        t.setStyle(
            TableStyle(
                [
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ]
            )
        )
        story.append(Paragraph("Latest vitals", styles["Heading2"]))
        story.append(t)
        story.append(Spacer(1, 12))

    # Recent findings (if table exists)
    try:
        _, findings = qn(
            dsn,
            """
            SELECT finding_time, metric, method, round(score::numeric,2) AS score, level
            FROM analytics.ai_findings
            ORDER BY finding_time DESC
            LIMIT 50""",
        )
        if findings:
            data = [["When", "Metric", "Method", "Score", "Level"]]
            for r in findings:
                data.append(
                    [
                        str(r["finding_time"]),
                        r["metric"],
                        r["method"],
                        r["score"],
                        r["level"],
                    ]
                )
            t = Table(data, hAlign="LEFT")
            t.setStyle(
                TableStyle(
                    [
                        ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                    ]
                )
            )
            story.append(Paragraph("Recent findings (top 50)", styles["Heading2"]))
            story.append(t)
            story.append(Spacer(1, 12))
    except Exception:
        story.append(Paragraph("Findings table not available.", styles["Italic"]))
        story.append(Spacer(1, 12))

    # Daily vitals narrow (pull from mv_daily_vitals if available)
    try:
        _, daily = qn(
            dsn,
            """
            SELECT day::date, hr_median, spo2_min
            FROM analytics.mv_vitals_daily_wide
            ORDER BY day DESC
            LIMIT 30
        """,
        )
        if daily:
            data = [["Day", "HR median", "SpO2 min (%)"]]
            for r in daily:
                spo2p = "" if r["spo2_min"] is None else f"{r['spo2_min']*100:.0f}"
                data.append([str(r["day"]), f"{(r['hr_median'] or 0):.0f}", spo2p])
            t = Table(data, hAlign="LEFT")
            t.setStyle(
                TableStyle(
                    [
                        ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                    ]
                )
            )
            story.append(Paragraph("Daily vitals (last 30 days)", styles["Heading2"]))
            story.append(t)
    except Exception:
        pass

    doc = SimpleDocTemplate(outpath, pagesize=A4)
    doc.build(story)
    return outpath


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dsn", default=dsn_from_env())
    ap.add_argument("--outdir", default=EXPORT_DIR)
    args = ap.parse_args()

    os.makedirs(args.outdir, exist_ok=True)
    out = os.path.join(args.outdir, f"health_report_{dt.date.today():%Y-%m-%d}.pdf")
    print(build_pdf(args.dsn, out))


if __name__ == "__main__":
    main()
