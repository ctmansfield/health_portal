from __future__ import annotations
from statistics import mean, pstdev
from typing import Iterable, List, Tuple, Optional


def rolling_zscore(
    series: Iterable[Tuple[str, float]], window: int = 21
) -> List[Tuple[str, Optional[float]]]:
    buf: List[float] = []
    out: List[Tuple[str, Optional[float]]] = []
    for ts, v in series:
        if v is None:
            out.append((ts, None))
            continue
        buf.append(v)
        if len(buf) > window:
            buf.pop(0)
        if len(buf) < max(5, window // 2):
            out.append((ts, None))
            continue
        m = mean(buf)
        s = pstdev(buf) or 0.0
        z = (v - m) / s if s > 0 else 0.0
        out.append((ts, z))
    return out


def level_from_score(score: float) -> str:
    a = abs(score)
    if a >= 3.0:
        return "alert"
    if a >= 2.0:
        return "warn"
    return "info"
