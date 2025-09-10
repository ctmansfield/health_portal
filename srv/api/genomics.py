from fastapi import APIRouter, Request, Depends, HTTPException, Response
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, StreamingResponse
from app.hp_etl.db import pg
from .auth import require_api_key
import os
import mimetypes

router = APIRouter()
templates = Jinja2Templates(directory="srv/api/templates")


@router.get("/genomics", response_class=HTMLResponse)
def genomics_index(
    request: Request, limit: int = 50, offset: int = 0, auth=Depends(require_api_key)
):
    """Render a list of genomics reports from analytics.genomics_reports."""
    sql = """
    SELECT report_id, person_id, filename, path, generated_at
    FROM analytics.genomics_reports
    ORDER BY generated_at DESC
    LIMIT %s OFFSET %s
    """
    items = []
    with pg() as conn:
        cur = conn.cursor()
        try:
            cur.execute(sql, (limit, offset))
            rows = cur.fetchall()
            cols = [c[0] for c in cur.description]
            for r in rows:
                items.append(dict(zip(cols, r)))
        except Exception:
            items = []
    return templates.TemplateResponse(
        "genomics.html", {"request": request, "reports": items}
    )


@router.get("/genomics/reports/{report_id}", response_class=HTMLResponse)
def genomics_report_page(
    request: Request, report_id: str, auth=Depends(require_api_key)
):
    sql = "SELECT report_id, person_id, filename, path, generated_at FROM analytics.genomics_reports WHERE report_id = %s"
    with pg() as conn:
        cur = conn.cursor()
        cur.execute(sql, (report_id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Report not found")
        cols = [c[0] for c in cur.description]
        report = dict(zip(cols, row))
    return templates.TemplateResponse(
        "genomics_report.html", {"request": request, "report": report}
    )


@router.get("/genomics/reports/{report_id}/download")
def genomics_report_download(report_id: str, auth=Depends(require_api_key)):
    sql = "SELECT path, filename FROM analytics.genomics_reports WHERE report_id = %s"
    with pg() as conn:
        cur = conn.cursor()
        cur.execute(sql, (report_id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Report not found")
        path, filename = row[0], row[1]
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="File not found")
    mime, _ = mimetypes.guess_type(filename)
    mime = mime or "application/octet-stream"

    def iterfile():
        with open(path, "rb") as fh:
            while True:
                chunk = fh.read(8192)
                if not chunk:
                    break
                yield chunk

    headers = {"Content-Disposition": f'inline; filename="{filename}"'}
    return StreamingResponse(iterfile(), media_type=mime, headers=headers)
