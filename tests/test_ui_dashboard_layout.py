from starlette.testclient import TestClient
from srv.api.main import app


def test_dashboard_layout_contains_grid_and_chart_wrap():
    client = TestClient(app)
    r = client.get("/dashboard")
    assert r.status_code == 200
    body = r.text
    assert 'class="dashboard-main"' in body
    assert 'class="chart-wrap"' in body
    assert 'class="summary-card"' in body
    # ensure the sparkline canvases are present
    assert 'id="hrSpark"' in body
    assert 'id="spo2Spark"' in body
