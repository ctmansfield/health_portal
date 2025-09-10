from fastapi import APIRouter, Query
import os, datetime as dt, subprocess
from hp_etl.db import dsn_from_env

router = APIRouter(tags=["export"])
EXPORT_DIR = "/mnt/nas_storage/exports"


def _run(cmd: list[str]) -> str:
    out = subprocess.check_output(cmd, text=True).strip()
    return out


@router.get("/export/pdf")
def export_pdf():
    os.makedirs(EXPORT_DIR, exist_ok=True)
    dsn = dsn_from_env()
    path = _run(["python", "jobs/export_pdf.py", "--dsn", dsn, "--outdir", EXPORT_DIR])
    return {"pdf": path}


@router.get("/export/bundle")
def export_bundle(include_pdf: bool = True):
    dsn = dsn_from_env()
    pdf = None
    if include_pdf:
        # try to use today's PDF or create one
        pdf = os.path.join(EXPORT_DIR, f"health_report_{dt.date.today():%Y-%m-%d}.pdf")
        if not os.path.exists(pdf):
            pdf = _run(
                ["python", "jobs/export_pdf.py", "--dsn", dsn, "--outdir", EXPORT_DIR]
            )
    bundle = _run(
        ["python", "jobs/export_bundle.py", "--dsn", dsn, "--outdir", EXPORT_DIR]
        + (["--pdf", pdf] if pdf else [])
    )
    return {"zip": bundle, "pdf": pdf}
