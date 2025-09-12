from starlette.testclient import TestClient
from srv.api.main import app

client = TestClient(app)


def test_labs_critical_page_renders():
    r = client.get("/ui/people/00000000-0000-0000-0000-000000000000/labs/critical")
    assert r.status_code == 200
    body = r.text
    assert 'class="hp-labs-critical"' in body
    assert "/static/js/labs_critical_v2.js" in body
