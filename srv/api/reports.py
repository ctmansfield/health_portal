from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
import app.hp_etl.db as db
import uuid

router = APIRouter()


@router.get("/reports/{id}")
def get_report(id: str):
    """Return the canonical report payload JSON stored in analytics.report.payload by report.id (UUID).

    - 200: returns JSON payload verbatim
    - 400: invalid id format
    - 404: not found
    """
    # validate uuid
    try:
        uid = uuid.UUID(id)
    except Exception:
        raise HTTPException(status_code=400, detail="invalid id format")

    sql = "SELECT payload FROM analytics.report WHERE id = %s"
    with db.pg() as conn:
        cur = conn.cursor()
        cur.execute(sql, (str(uid),))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Report not found")
        payload = row[0]

    # Return payload verbatim with PHI-safe headers
    return JSONResponse(
        content=payload,
        media_type="application/json; charset=utf-8",
        headers={"Cache-Control": "no-store"},
    )
