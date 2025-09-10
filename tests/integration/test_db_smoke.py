import os
import subprocess
import sys
import time
import pytest

from fastapi.testclient import TestClient


@pytest.mark.integration
def test_db_migrations_seed_and_dashboard_smoke():
    """Integration smoke test:
    - requires HP_DSN to be set and a reachable Postgres instance (local dev docker compose recommended)
    - applies migrations, seeds data, refreshes materialized views, and hits dashboard/genomics endpoints
    """
    dsn = os.environ.get("HP_DSN")
    if not dsn:
        pytest.skip("HP_DSN not set; skipping integration test")

    # Apply migrations (best-effort)
    subprocess.check_call(
        ["bash", "scripts/db/apply_migrations.sh"]
    )  # exits non-zero on error

    # Seed sample data
    subprocess.check_call(
        [
            sys.executable,
            "jobs/seed_sample_data.py",
            "--dsn",
            dsn,
            "--genomics",
            "--findings",
            "--days",
            "10",
        ]
    )

    # Refresh materialized views
    subprocess.check_call(
        [sys.executable, "jobs/refresh_materialized_views.py", "--dsn", dsn]
    )

    # Allow DB a moment to settle
    time.sleep(1)

    # Import app and run a smoke test using TestClient
    from srv.api.main import app

    client = TestClient(app)

    r = client.get("/dashboard")
    assert r.status_code == 200
    assert "Health Portal" in r.text or "Median HR" in r.text

    r = client.get("/genomics")
    # genomics may require HP_API_KEY or sessions; if HP_API_KEY is not set, the repo allows dev access
    assert r.status_code in (
        200,
        302,
        401,
    )  # allow 401 in strict setups; CI can set HP_API_KEY

    # basic JSON events endpoint
    r = client.get("/dashboard/events.json?person_id=me&limit=5")
    assert r.status_code == 200
    j = r.json()
    assert isinstance(j, list)
