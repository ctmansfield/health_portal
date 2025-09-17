from fastapi import APIRouter, Path, Query, HTTPException
from typing import List, Dict, Any
import os
import psycopg
from psycopg.rows import dict_row

router = APIRouter(prefix="/labs", tags=["labs"])


def _conninfo() -> str:
    # Prefer DATABASE_URL; else build from PG* env vars
    url = os.getenv("DATABASE_URL")
    if url:
        return url
    host = os.getenv("PGHOST", "localhost")
    port = os.getenv("PGPORT", "5432")
    db = os.getenv("PGDATABASE", "postgres")
    user = os.getenv("PGUSER", "postgres")
    pwd = os.getenv("PGPASSWORD", "")
    return f"postgresql://{user}:{pwd}@{host}:{port}/{db}"


@router.get("/{person_id}/labs-metadata", response_model=List[Dict[str, Any]])
def labs_metadata(
    person_id: str = Path(..., description="Patient/person identifier"),
    include_sensitive: bool = Query(
        True, description="Include items flagged Sensitive"
    ),
) -> List[Dict[str, Any]]:
    try:
        with psycopg.connect(_conninfo(), row_factory=dict_row) as conn:
            if include_sensitive:
                sql = """
                    SELECT label, group_name, sensitive
                    FROM analytics.v_labs_metadata_person
                    WHERE person_id = %s
                    ORDER BY group_name, label
                """
                params = (person_id,)
            else:
                sql = """
                    SELECT label, group_name, sensitive
                    FROM analytics.v_labs_metadata_person
                    WHERE person_id = %s AND NOT sensitive
                    ORDER BY group_name, label
                """
                params = (person_id,)
            rows = conn.execute(sql, params).fetchall()
        return rows
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"labs-metadata query failed: {e}")
