from fastapi import APIRouter, HTTPException, Query
import os
import psycopg

router = APIRouter(prefix="/records", tags=["records"])
PG_DSN = (
    os.environ.get("PG_DSN")
    or "host=localhost port=5432 dbname=health_portal user=postgres"
)


def _rows(cur):
    cols = [d.name for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


@router.get("/{person_id}/browse")
def browse(person_id: str, kind: str = Query("lab", pattern="^(lab|note|imaging)$")):
    try:
        with psycopg.connect(PG_DSN) as conn:
            if kind == "lab":
                cur = conn.execute(
                    """
                  SELECT observed_at AS ts, loinc_code, test_name, value_num, unit
                  FROM clinical.lab_result
                  WHERE person_id=%s ORDER BY observed_at DESC LIMIT 500
                """,
                    (person_id,),
                )
                return {"kind": "lab", "items": _rows(cur)}
            elif kind == "note":
                cur = conn.execute(
                    """
                  SELECT authored_at AS ts, note_type, title
                  FROM clinical.clinical_note
                  WHERE person_id=%s ORDER BY authored_at DESC LIMIT 200
                """,
                    (person_id,),
                )
                return {"kind": "note", "items": _rows(cur)}
            else:  # imaging
                cur = conn.execute(
                    """
                  SELECT started_at AS ts, study_uid, modality, description
                  FROM imaging.imaging_study
                  WHERE person_id=%s ORDER BY started_at DESC LIMIT 200
                """,
                    (person_id,),
                )
                return {"kind": "imaging", "items": _rows(cur)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{person_id}/browse_notes")
def browse_notes(person_id: str):
    try:
        with psycopg.connect(PG_DSN) as conn:
            cur = conn.execute(
                """
              SELECT authored_at AS ts, note_type, title
              FROM clinical.clinical_note
              WHERE person_id=%s ORDER BY authored_at DESC LIMIT 200
            """,
                (person_id,),
            )
            return {"kind": "note", "items": _rows(cur)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{person_id}/browse_imaging")
def browse_imaging(person_id: str):
    try:
        with psycopg.connect(PG_DSN) as conn:
            cur = conn.execute(
                """
              SELECT started_at AS ts, study_uid, modality, description
              FROM imaging.imaging_study
              WHERE person_id=%s ORDER BY started_at DESC LIMIT 200
            """,
                (person_id,),
            )
            return {"kind": "imaging", "items": _rows(cur)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
