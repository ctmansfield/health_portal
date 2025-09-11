import logging
from uuid import UUID
from datetime import datetime
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import text
from sqlalchemy.orm import Session

router = APIRouter()
logger = logging.getLogger(__name__)


def _fallback_get_db():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}
    )
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


try:
    from app.db.dependencies import get_db  # type: ignore
except Exception:
    get_db = _fallback_get_db


def _execute_query(db: Session, sql: str, params: Dict[str, Any]):
    try:
        return db.execute(text(sql), params)
    except AttributeError:
        return db.execute(sql, params)


@router.get("/reports/{id}/summary")
def get_report_summary(id: str, db: Session = Depends(get_db)):
    # Validate UUID
    try:
        uuid_obj = UUID(id)
    except Exception:
        logger.info("get_report_summary invalid_uuid id=%s -> 400", id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid id"
        )

    sql = """
SELECT id, title, result, signed_out_at
FROM report_exec_summary
WHERE id = :id
"""

    try:
        result = _execute_query(db, sql, {"id": str(uuid_obj)})
        row = result.fetchone()
    except Exception:
        logger.exception("get_report_summary db_error id=%s", id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Server error"
        )

    if not row:
        logger.info("get_report_summary not_found id=%s -> 404", id)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    # tolerant row mapping (tuple or Row object)
    try:
        payload = {
            "id": row.id if hasattr(row, "id") else row[0],
            "title": row.title if hasattr(row, "title") else row[1],
            "result": row.result if hasattr(row, "result") else row[2],
            "signed_out_at": (
                row.signed_out_at if hasattr(row, "signed_out_at") else row[3]
            ),
        }
    except Exception:
        try:
            keys = result.keys()  # type: ignore
            payload = {
                k: row[i]
                for i, k in enumerate(keys)
                if k in ("id", "title", "result", "signed_out_at")
            }
        except Exception:
            logger.exception("get_report_summary row_map_error id=%s", id)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Server error"
            )

    if isinstance(payload.get("signed_out_at"), datetime):
        payload["signed_out_at"] = payload["signed_out_at"].isoformat()

    if not all(
        k in payload and payload[k] is not None
        for k in ("id", "title", "result", "signed_out_at")
    ):
        logger.info("get_report_summary incomplete_row id=%s -> 404", id)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    logger.info("get_report_summary ok id=%s -> 200", id)
    return Response(
        content=__import__("json").dumps(payload),
        media_type="application/json; charset=utf-8",
        headers={"Cache-Control": "no-store"},
        status_code=status.HTTP_200_OK,
    )
