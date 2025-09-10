from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Callable, Iterable, Optional, List


def parse_isoz(s: str) -> datetime:
    """Parse ISO 8601 with Z as UTC, or assume UTC if no tz."""
    if s.endswith("Z"):
        return datetime.fromisoformat(s[:-1]).replace(tzinfo=timezone.utc)
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def isoz(dt: datetime) -> str:
    """Format to ISO Z string."""
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def floor_dt(dt: datetime, freq: str) -> datetime:
    """Floor datetime to UTC bucket."""
    dt = dt.astimezone(timezone.utc)
    if freq == "1min":
        return dt.replace(second=0, microsecond=0)
    elif freq == "5min":
        return dt.replace(minute=(dt.minute // 5) * 5, second=0, microsecond=0)
    elif freq == "15min":
        return dt.replace(minute=(dt.minute // 15) * 15, second=0, microsecond=0)
    elif freq == "1h":
        return dt.replace(minute=0, second=0, microsecond=0)
    elif freq == "1d":
        return dt.replace(hour=0, minute=0, second=0, microsecond=0)
    else:
        raise ValueError(f"Unsupported freq: {freq}")


@dataclass
class Point:
    ts: str
    v: Optional[float]


def agg_mean(xs: list[float]) -> Optional[float]:
    xs = [x for x in xs if x is not None]
    if not xs:
        return None
    return sum(xs) / len(xs)


def resample(
    points: Iterable[Point],
    freq: str,
    agg: Callable[[list[float]], Optional[float]] = agg_mean,
) -> List[Point]:
    """Bin by floored UTC time, aggregate values per bin."""
    buckets = {}
    for p in points:
        if p.v is None:
            continue
        dt = parse_isoz(p.ts)
        key = floor_dt(dt, freq)
        buckets.setdefault(key, []).append(p.v)
    out = [Point(isoz(k), agg(vs)) for k, vs in sorted(buckets.items())]
    return out
