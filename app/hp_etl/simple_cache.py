"""Simple process-local TTL cache used by dashboard queries.
Note: this is an in-memory per-process cache suitable for low-volume dashboards.
For multi-worker deployments consider an external cache (Redis).
"""

import time
import threading
from typing import Any, Optional

_cache = {}
_lock = threading.Lock()


def get(key: str) -> Optional[Any]:
    with _lock:
        ent = _cache.get(key)
        if not ent:
            return None
        val, expires = ent
        if expires is not None and time.time() > expires:
            del _cache[key]
            return None
        return val


def set(key: str, value: Any, ttl: Optional[int] = None) -> None:
    expires = time.time() + ttl if ttl else None
    with _lock:
        _cache[key] = (value, expires)


def clear(key: str) -> None:
    with _lock:
        _cache.pop(key, None)


def clear_all() -> None:
    with _lock:
        _cache.clear()
