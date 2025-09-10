"""Optional Redis-backed session helpers.
Falls back to no-ops when redis isn't available. Values stored in Redis are JSON with keys: user_id, expires.
"""

import os
import json

REDIS_URL = os.environ.get("REDIS_URL")
_redis = None
if REDIS_URL:
    try:
        import redis

        _redis = redis.from_url(REDIS_URL)
    except Exception:
        _redis = None


def _redis_key(sid: str) -> str:
    return f"hp:sess:{sid}"


def set_redis_session(sid: str, user_id: int, expires_iso: str) -> None:
    if not _redis:
        return
    val = json.dumps({"user_id": user_id, "expires": expires_iso})
    # set ttl based on iso parse in caller; here we just set without ttl
    _redis.set(_redis_key(sid), val)


def get_redis_session(sid: str):
    if not _redis:
        return None
    v = _redis.get(_redis_key(sid))
    if not v:
        return None
    try:
        obj = json.loads(v)
        return obj.get("user_id"), obj.get("expires")
    except Exception:
        return None


def delete_redis_session(sid: str) -> None:
    if not _redis:
        return
    _redis.delete(_redis_key(sid))
