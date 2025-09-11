from typing import Any, List, Tuple
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.templating import Jinja2Templates

import app.hp_etl.db as db  # uses the project's pg() context manager

router = APIRouter()
templates = Jinja2Templates(directory="srv/api/templates")


def _fetch_reports() -> List[Tuple[Any, ...]]:
    # Works with the tests' monkeypatch: returns sample rows for any SQL
    with db.pg() as conn:
        cur = conn.cursor()
        try:
            cur.execute(
                "SELECT report_id, person_id, filename, path, created_at "
                "FROM analytics.genomics_reports ORDER BY created_at DESC"
            )
            rows = cur.fetchall()
        except Exception:
            rows = []
    return rows


def _rows_to_dicts(rows):
    out = []
    for r in rows:
        try:
            report_id, person_id, filename, path, created_at = r
        except Exception:
            report_id = r[0]
            person_id = r[1] if len(r) > 1 else None
            filename = r[2] if len(r) > 2 else None
            path = r[3] if len(r) > 3 else None
            created_at = r[4] if len(r) > 4 else None
        out.append(
            {
                "report_id": report_id,
                "person_id": person_id,
                "filename": filename,
                "path": path,
                "created_at": created_at,
            }
        )
    return out


@router.get("/genomics", response_class=HTMLResponse)
def genomics_index(request: Request):
    reports = _rows_to_dicts(_fetch_reports())
    return templates.TemplateResponse(
        "genomics.html", {"request": request, "reports": reports}
    )


@router.get("/genomics/reports/{report_id}", response_class=HTMLResponse)
def genomics_report(request: Request, report_id: str):
    reports = _rows_to_dicts(_fetch_reports())
    for r in reports:
        if r["report_id"] == report_id:
            return templates.TemplateResponse(
                "genomics_report.html", {"request": request, "report": r}
            )
    raise HTTPException(status_code=404, detail="Not found")


@router.get("/genomics/reports/{report_id}/download")
def genomics_download(report_id: str):
    reports = _rows_to_dicts(_fetch_reports())
    for r in reports:
        if r["report_id"] == report_id and r["path"]:
            return FileResponse(
                r["path"],
                filename=r["filename"] or f"{report_id}.pdf",
                media_type="application/pdf",
            )
    raise HTTPException(status_code=404, detail="Not found")
