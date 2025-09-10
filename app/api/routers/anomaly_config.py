from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from hp_etl.db import pg, dsn_from_env

router = APIRouter(tags=["anomalies-config"])


class Threshold(BaseModel):
    code: str = Field(..., description="LOINC code, e.g., 8867-4")
    min_val: Optional[float] = None
    max_val: Optional[float] = None
    reason: Optional[str] = "out of configured range"
    enabled: bool = True


@router.get("/anomalies/thresholds")
def list_thresholds() -> Dict[str, Any]:
    dsn = dsn_from_env()
    with pg(dsn) as conn, conn.cursor() as cur:
        cur.execute(
            """
          SELECT code, min_val, max_val, reason, enabled, updated_at
          FROM analytics.anomaly_thresholds
          ORDER BY code
        """
        )
        cols = [d.name for d in cur.description]
        rows = [dict(zip(cols, r)) for r in cur.fetchall()]
    return {"rows": rows}


@router.put("/anomalies/thresholds/{code}")
def upsert_threshold(code: str, body: Threshold) -> Dict[str, Any]:
    if code != body.code:
        raise HTTPException(
            status_code=400, detail="Path code and body code must match"
        )
    dsn = dsn_from_env()
    with pg(dsn) as conn, conn.cursor() as cur:
        cur.execute(
            """
          INSERT INTO analytics.anomaly_thresholds (code, min_val, max_val, reason, enabled, updated_at)
          VALUES (%(code)s, %(min_val)s, %(max_val)s, %(reason)s, %(enabled)s, now())
          ON CONFLICT (code) DO UPDATE SET
            min_val   = EXCLUDED.min_val,
            max_val   = EXCLUDED.max_val,
            reason    = EXCLUDED.reason,
            enabled   = EXCLUDED.enabled,
            updated_at= now()
          RETURNING code, min_val, max_val, reason, enabled, updated_at
        """,
            body.model_dump(),
        )
        row = cur.fetchone()
        cols = [d.name for d in cur.description]
    return {"row": dict(zip(cols, row))}
