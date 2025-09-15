#!/usr/bin/env python3
import argparse
import os
import datetime as dt
from hp_etl.db import pg, dsn_from_env

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.graphics.shapes import Drawing, String
from reportlab.graphics.charts.lineplots import LinePlot


def fetch_latest_vitals(dsn: str):
    sql = """
    SELECT person_id,
           hr_latest,
           spo2_latest,
           updated_at
    FROM analytics.v_vitals_latest
    ORDER BY person_id
    """
    with pg(dsn) as conn, conn.cursor() as cur:
        cur.execute(sql)
        cols = [d.name for d in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]


def fetch_daily_vitals(dsn: str, days: int = 30):
    sql = """
    SELECT day::date, hr_median, spo2_min
    FROM analytics.mv_vitals_daily_wide
    WHERE day >= current_date - %s::int
    ORDER BY day
    """
    with pg(dsn) as conn, conn.cursor() as cur:
        cur.execute(sql, (days,))
        return cur.fetchall()


def vitals_chart(rows):
    # rows: [(date, hr_median, spo2_min)]
    dw, dh = 440, 180
    d = Drawing(dw, dh)

    if not rows:
        d.add(String(10, dh / 2 - 6, "No daily vitals to plot.", fontSize=10))
        return d

    # xs unused; remove to satisfy lint
    hr = [(i, float(r[1])) for i, r in enumerate(rows) if r[1] is not None]
    sp = [(i, float(r[2]) * 100.0) for i, r in enumerate(rows) if r[2] is not None]

    lp = LinePlot()
    lp.x = 40
    lp.y = 30
    lp.width = dw - 60
    lp.height = dh - 60
    series = []
    if hr:
        series.append(hr)
    if sp:
        series.append(sp)

    if not series:
        d.add(String(10, dh / 2 - 6, "No numeric values available.", fontSize=10))
        return d

    lp.data = series
    lp.joinedLines = True
    lp.lines[0].strokeColor = colors.HexColor("#1f77b4")  # hr
    if len(series) > 1:
        lp.lines[1].strokeColor = colors.HexColor("#2ca02c")  # SpO2

    # X labels: show first, middle, last dates to avoid clutter
    labels = []
    dates = [r[0].isoformat() for r in rows]
    for i in [0, len(rows) // 2, len(rows) - 1]:
        if 0 <= i < len(rows):
            labels.append((i, 0, dates[i]))
    lp.xValueAxis.visibleGrid = False
    lp.yValueAxis.visibleGrid = True
    d.add(lp)

    # Simple legend
    y0 = dh - 15
    d.add(String(40, y0, "HR (bpm)", fontSize=9, fillColor=colors.HexColor("#1f77b4")))
    d.add(String(120, y0, "SpO2 (%)", fontSize=9, fillColor=colors.HexColor("#2ca02c")))

    return d


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dsn", default=dsn_from_env())
    ap.add_argument("--days", type=int, default=30)
    ap.add_argument("--outdir", default="/mnt/nas_storage/exports")
    args = ap.parse_args()

    os.makedirs(args.outdir, exist_ok=True)
    today = dt.date.today().isoformat()
    outpath = os.path.join(args.outdir, f"health_report_{today}.pdf")

    doc = SimpleDocTemplate(outpath, pagesize=A4, title="Health Report")
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

    # Latest vitals table
    latest = fetch_latest_vitals(args.dsn)
    table_data = [["Person", "HR (bpm)", "SpO2 (%)", "Updated (UTC)"]]
    for r in latest:
        hr = f"{int(r['hr_latest'])}" if r["hr_latest"] is not None else "—"
        sp = (
            f"{round(float(r['spo2_latest']) * 100.0, 1)}"
            if r["spo2_latest"] is not None
            else "—"
        )
        ts = r["updated_at"].isoformat() if r["updated_at"] else "—"
        table_data.append([r["person_id"], hr, sp, ts])

    t = Table(table_data, hAlign="LEFT")
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f0f0f0")),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
            ]
        )
    )
    story.append(Paragraph("Latest vitals", styles["Heading2"]))
    story.append(t)
    story.append(Spacer(1, 12))

    # 30-day chart
    rows = fetch_daily_vitals(args.dsn, args.days)
    story.append(Paragraph(f"Daily vitals (last {args.days} days)", styles["Heading2"]))
    story.append(vitals_chart(rows))
    story.append(Spacer(1, 12))

    # Recent findings (if present)
    with pg(args.dsn) as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT finding_time, metric, method, round(score::numeric,2) AS score, level
            FROM analytics.ai_findings
            WHERE finding_time >= now() - interval '30 days'
            ORDER BY finding_time DESC
            LIMIT 50
        """
        )
        cols = [d.name for d in cur.description]
        findings = [dict(zip(cols, r)) for r in cur.fetchall()]

    if findings:
        fd = [["When (UTC)", "Metric", "Score", "Level", "Method"]] + [
            [
                f["finding_time"].isoformat(),
                f["metric"],
                f["score"],
                f["level"],
                f["method"],
            ]
            for f in findings
        ]
        tf = Table(fd, hAlign="LEFT")
        tf.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f0f0f0")),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ]
            )
        )
        story.append(Paragraph("Recent AI findings", styles["Heading2"]))
        story.append(tf)

    doc.build(story)
    print(outpath)


if __name__ == "__main__":
    main()
