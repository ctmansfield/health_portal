from fastapi import APIRouter, Query
import subprocess, os

router = APIRouter(prefix="/fhir", tags=["fhir"])


@router.post("/import")
def import_observations(
    person_id: str = "me", since: str | None = None, limit: int = 0
):
    dsn = os.getenv("HP_DSN")
    cmd = [
        "python",
        "jobs/map_fhir_to_events.py",
        "--dsn",
        dsn,
        "--person-id",
        person_id,
    ]
    if since:
        cmd.extend(["--since", since])
    if limit:
        cmd.extend(["--limit", str(limit)])
    out = subprocess.run(cmd, capture_output=True, text=True)
    return {
        "ok": out.returncode == 0,
        "stdout": out.stdout[-500:],  # last 500 chars
        "stderr": out.stderr[-500:],
    }
