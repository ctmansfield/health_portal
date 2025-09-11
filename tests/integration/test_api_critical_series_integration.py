import os
import subprocess
import time
import socket
import textwrap
import psycopg
import json
import uuid
from contextlib import closing
import pytest
from starlette.testclient import TestClient
from srv.api.main import app

DOCKER_ENV = os.environ.get("HP_DOCKER_TEST", "0")


def _docker_available():
    try:
        subprocess.run(
            ["docker", "version"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )
        return True
    except Exception:
        return False


@pytest.mark.integration
def test_integration_critical_series_docker():
    if DOCKER_ENV != "1":
        pytest.skip("Set HP_DOCKER_TEST=1 to enable docker integration tests")
    if not _docker_available():
        pytest.skip("Docker not available on this host")

    # Run a temporary postgres container with random host port
    print("Starting postgres docker container for integration test...")
    cid = (
        subprocess.check_output(
            [
                "docker",
                "run",
                "-d",
                "-e",
                "POSTGRES_PASSWORD=health_pw",
                "-e",
                "POSTGRES_USER=health",
                "-e",
                "POSTGRES_DB=health",
                "-P",
                "postgres:15",
            ]
        )
        .decode()
        .strip()
    )

    try:
        # find mapped port
        port_out = (
            subprocess.check_output(["docker", "port", cid, "5432"]).decode().strip()
        )
        # port_out looks like '0.0.0.0:32768'
        host_port = int(port_out.split(":")[1])
        dsn = f"postgresql://health:health_pw@localhost:{host_port}/health"

        # wait for postgres to accept connections
        deadline = time.time() + 60
        connected = False
        while time.time() < deadline:
            try:
                with psycopg.connect(dsn) as conn:
                    with conn.cursor() as cur:
                        cur.execute("SELECT 1")
                        connected = True
                        break
            except Exception:
                time.sleep(1)
        if not connected:
            raise RuntimeError("Postgres container did not become ready in time")

        # initialize minimal schema and seed test data
        with psycopg.connect(dsn, autocommit=True) as conn:
            cur = conn.cursor()
            cur.execute("CREATE SCHEMA IF NOT EXISTS analytics")
            cur.execute(
                textwrap.dedent(
                    """
                CREATE TABLE IF NOT EXISTS analytics.person (
                    person_id text PRIMARY KEY,
                    tz text
                )
            """
                )
            )
            cur.execute(
                textwrap.dedent(
                    """
                CREATE TABLE IF NOT EXISTS analytics.mv_daily_vitals (
                    day date,
                    person_id text,
                    hr_median numeric,
                    spo2_min numeric
                )
            """
                )
            )
            cur.execute(
                textwrap.dedent(
                    """
                CREATE TABLE IF NOT EXISTS analytics.data_events (
                    person_id text,
                    source text,
                    kind text,
                    code_system text,
                    code text,
                    value_num numeric,
                    unit text,
                    effective_time timestamptz,
                    meta jsonb
                )
            """
                )
            )
            cur.execute(
                textwrap.dedent(
                    """
                CREATE TABLE IF NOT EXISTS analytics.etl_state (
                    key text PRIMARY KEY,
                    value text
                )
            """
                )
            )
            # seed person with tz
            cur.execute(
                "INSERT INTO analytics.person (person_id, tz) VALUES (%s, %s) ON CONFLICT (person_id) DO NOTHING",
                ("integration_user", "America/Los_Angeles"),
            )
            # seed daily vitals
            cur.execute(
                "INSERT INTO analytics.mv_daily_vitals (day, person_id, hr_median, spo2_min) VALUES (%s,%s,%s,%s)",
                ("2025-09-01", "integration_user", 60, 98),
            )
            cur.execute(
                "INSERT INTO analytics.mv_daily_vitals (day, person_id, hr_median, spo2_min) VALUES (%s,%s,%s,%s)",
                ("2025-09-02", "integration_user", 62, 97),
            )
            # seed raw events for hourly
            cur.execute(
                "INSERT INTO analytics.data_events (person_id, source, kind, code_system, code, value_num, unit, effective_time, meta) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (
                    "integration_user",
                    "device",
                    "observation",
                    "loinc",
                    "8867-4",
                    61,
                    "bpm",
                    "2025-09-01T03:10:00Z",
                    json.dumps({}),
                ),
            )
            cur.execute(
                "INSERT INTO analytics.data_events (person_id, source, kind, code_system, code, value_num, unit, effective_time, meta) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (
                    "integration_user",
                    "device",
                    "observation",
                    "loinc",
                    "8867-4",
                    63,
                    "bpm",
                    "2025-09-02T04:20:00Z",
                    json.dumps({}),
                ),
            )
            # set etl state version
            cur.execute(
                "INSERT INTO analytics.etl_state (key, value) VALUES (%s,%s) ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value",
                ("mv_daily_vitals_version", "v1"),
            )

        # set HP_DSN env for app to use
        os.environ["HP_DSN"] = dsn

        client = TestClient(app)
        # daily agg
        r = client.get(
            "/labs/integration_user/critical-series?metrics=hr,spo2&since=2025-09-01&until=2025-09-02"
        )
        assert r.status_code == 200
        body = r.json()
        assert any(x["metric"] == "hr" for x in body)
        # hourly agg
        r2 = client.get(
            "/labs/integration_user/critical-series?metrics=hr&agg=hourly&since=2025-09-01T00:00:00Z&until=2025-09-02T23:59:59Z"
        )
        assert r2.status_code == 200
        body2 = r2.json()
        assert len(body2) == 1
        hr = body2[0]
        assert hr["metric"] == "hr"
        assert "series" in hr
        # verify timestamps include t_utc and t_local
        for pt in hr["series"]:
            assert "t" in pt or "t_utc" in pt or "t_local" in pt

    finally:
        # cleanup container
        try:
            subprocess.run(
                ["docker", "rm", "-f", cid],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception:
            pass
