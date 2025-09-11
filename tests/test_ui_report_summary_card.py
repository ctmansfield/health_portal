from starlette.testclient import TestClient
from srv.api.main import app


def test_ui_component_partial_renders():
    client = TestClient(app)
    r = client.get("/ui/components/report-summary-card?id=00000000-0000-0000-0000-000000000000")
    assert r.status_code == 200
    body = r.text
    assert 'class="hp-report-summary-card"' in body
    assert '/static/js/report_summary_card.js' in body
    # headers
    assert r.headers.get('cache-control') == 'no-store'


def test_ui_page_renders():
    client = TestClient(app)
    r = client.get("/ui/reports/00000000-0000-0000-0000-000000000000/summary-card")
    assert r.status_code == 200
    assert 'class="hp-report-summary-card"' in r.text
    assert r.headers.get('cache-control') == 'no-store'
