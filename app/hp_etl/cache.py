"""Cache abstraction: uses Redis if REDIS_URL is set and redis package available,
otherwise falls back to the process-local simple_cache implementation.
"""

from typing import Any, Optional
import os

_use_redis = False
_redis_client = None

try:
    import redis

    # Prefer Redis. Default to localhost if REDIS_URL not set so switching to Redis is simple for local dev.
    REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    try:
        _redis_client = redis.from_url(REDIS_URL)
        # attempt a quick ping to verify availability
        _redis_client.ping()
        _use_redis = True
    except Exception:
        _use_redis = False
        _redis_client = None
except Exception:
    _use_redis = False
    _redis_client = None

if not _use_redis:
    # fallback to process-local cache
    from .simple_cache import (
        get as _get_local,
        set as _set_local,
        clear as _clear_local,
    )


def get(key: str) -> Optional[Any]:
    if _use_redis and _redis_client:
        try:
            raw = _redis_client.get(key)
            if raw is None:
                return None
            # stored as JSON via Redis
            import json

            return json.loads(raw)
        except Exception:
            return None
    else:
        return _get_local(key)


def set(key: str, value: Any, ttl: Optional[int] = None) -> None:
    if _use_redis and _redis_client:
        try:
            import json

            raw = json.dumps(value)
            if ttl:
                _redis_client.setex(key, int(ttl), raw)
            else:
                _redis_client.set(key, raw)
        except Exception:
            return None
    else:
        _set_local(key, value, ttl=ttl)


def clear(key: str) -> None:
    if _use_redis and _redis_client:
        try:
            _redis_client.delete(key)
        except Exception:
            pass
    else:
        _clear_local(key)
