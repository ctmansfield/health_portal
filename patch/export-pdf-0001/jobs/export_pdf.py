#!/usr/bin/env python3
import argparse, datetime as dt, os
from hp_etl.db import pg, dsn_from_env

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.charts.lineplots import LinePlot
from reportlab.graphics.widgets.markers import makeMarker


def fetch_latest_vitals(dsn: str):
    sql = "SELECT person_id, hr_latest, spo2_latest, updated_at FROM analytics.v_vitals_latest ORDER BY person_id"
    with pg(dsn) as conn, conn.cursor() as cur:
        cur.execute(sql)
        cols = [d.name for d in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]


def fetch_daily_vitals(dsn: str, days: int = 30):
    sql = """
    SELECT day::date, hr_median, spo2_min
    FROM analytics.mv_vitals_daily_wide
    WHERE day >= current_date - %s::int
    ORDER BY day;
    """
    with pg(dsn) as conn, conn.cursor() as cur:
        cur.execute(sql, (days,))
        return cur.fetchall()


def fetch_recent_findings(dsn: str, days: int = 30, limit: int = 50):
    sql = """
    SELECT finding_time, metric, method, round(score::numeric,2) AS score, level
    FROM analytics.ai_findings
    WHERE finding_time >= now() - make_interval(days => %s)
    ORDER BY finding_time DESC
    LIMIT %s;
    """
    with pg(dsn) as conn, conn.cursor() as cur:
        cur.execute(sql, (days, limit))
        cols = [d.name for d in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]


def vitals_chart(rows):
    # rows: list[(day, hr_median, spo2_min)]
    if not rows:
        return Drawing(400, 160)
    x = list(range(len(rows)))
    hr = [(i, float(r[1])) for i, r in enumerate(rows) if r[1] is not None]
    sp = [
        (i, float(r[2]) * 100.0) for i, r in enumerate(rows) if r[2] is not None
    ]  # % view
    d = Drawing(400, 160)
    lp = LinePlot()
    lp.height = 140
    lp.width = 380
    lp.x = 10
    lp.y = 10
    if hr:
        lp.data.append(hr)
    if sp:
        lp.data.append(sp)
    lp.joinedLines = True
    for i in range(len(lp.data)):
        lp.lines[i].strokeWidth = 1.5
        lp.lines[i].symbol = makeMarker("Circle")
    lp.xValueAxis.valueMin = 0
    lp.xValueAxis.valueMax = max(x) if x else 1
    lp.xValueAxis.visible = False
    lp.yValueAxis.labelTextFormat = "%0.0f"
    d.add(lp)
    return d


def build_pdf(path: str, dsn: str, days: int):
    doc = SimpleDocTemplate(path, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("Health Report", styles["Title"]))
    story.append(
        Paragraph(
            dt.datetime.now(dt.timezone.utc).strftime("Generated: %Y-%m-%d %H:%M UTC"),
            styles["Normal"],
        )
    )
    story.append(Spacer(1, 12))

    latest = fetch_latest_vitals(dsn)
    if latest:
        story.append(Paragraph("Latest Vitals", styles["Heading2"]))
        data = [["Person", "HR (bpm)", "SpO2 (%)", "Updated (UTC)"]]
        for r in latest:
            spo2 = r["spo2_latest"]
            data.append(
                [
                    r["person_id"],
                    r["hr_latest"],
                    None if spo2 is None else round(spo2 * 100.0, 1),
                    r["updated_at"],
                ]
            )
        t = Table(data, hAlign="LEFT")
        t.setStyle(
            TableStyle(
                [
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
                ]
            )
        )
        story.append(t)
        story.append(Spacer(1, 12))

    dv = fetch_daily_vitals(dsn, days)
    story.append(Paragraph(f"Daily Vitals (last {days} days)", styles["Heading2"]))
    story.append(vitals_chart(dv))
    story.append(Spacer(1, 12))

    findings = fetch_recent_findings(dsn, days)
    story.append(
        Paragraph(f"Recent AI Findings (last {days} days)", styles["Heading2"])
    )
    fdata = [["When (UTC)", "Metric", "Method", "Score", "Level"]]
    for r in findings:
        fdata.append(
            [r["finding_time"], r["metric"], r["method"], r["score"], r["level"]]
        )
    t2 = Table(fdata, hAlign="LEFT")
    t2.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
            ]
        )
    )
    story.append(t2)

    doc.build(story)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dsn", default=dsn_from_env())
    ap.add_argument("--outdir", default="/mnt/nas_storage/exports")
    ap.add_argument("--days", type=int, default=30)
    args = ap.parse_args()
    os.makedirs(args.outdir, exist_ok=True)
    fn = f"health_report_{dt.date.today().isoformat()}.pdf"
    path = os.path.join(args.outdir, fn)
    build_pdf(path, args.dsn, args.days)
    print(path)


if __name__ == "__main__":
    main()
