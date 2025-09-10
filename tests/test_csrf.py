import pytest
from app.hp_etl.csrf import require_csrf
from fastapi import HTTPException


class Req:
    def __init__(self, cookies, headers):
        self.cookies = cookies
        self.headers = headers


import asyncio


def run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def test_require_csrf_missing():
    r = Req({}, {})
    with pytest.raises(HTTPException) as ei:
        run(require_csrf(r))
    assert ei.value.status_code == 403


def test_require_csrf_mismatch():
    r = Req({"hp_csrf": "a"}, {"x-csrf-token": "b"})
    with pytest.raises(HTTPException) as ei:
        run(require_csrf(r))
    assert ei.value.status_code == 403


def test_require_csrf_ok():
    r = Req({"hp_csrf": "tok"}, {"x-csrf-token": "tok"})
    assert run(require_csrf(r)) is True
