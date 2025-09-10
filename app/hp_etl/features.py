from typing import Iterable, Optional, List
import math


def sma(xs: Iterable[float], window: int) -> List[Optional[float]]:
    xs = list(xs)
    out: List[Optional[float]] = []
    for i in range(len(xs)):
        if i + 1 < window:
            out.append(None)
        else:
            chunk = xs[i + 1 - window : i + 1]
            out.append(sum(chunk) / window)
    return out


def ema(xs: Iterable[float], alpha: float) -> List[Optional[float]]:
    out: List[Optional[float]] = []
    val = None
    for x in xs:
        if val is None:
            val = x
        else:
            val = alpha * x + (1 - alpha) * val
        out.append(val)
    return out


def rolling_min(xs: List[float], window: int) -> List[Optional[float]]:
    out: List[Optional[float]] = []
    for i in range(len(xs)):
        if i + 1 < window:
            out.append(None)
        else:
            out.append(min(xs[i + 1 - window : i + 1]))
    return out


def rolling_max(xs: List[float], window: int) -> List[Optional[float]]:
    out: List[Optional[float]] = []
    for i in range(len(xs)):
        if i + 1 < window:
            out.append(None)
        else:
            out.append(max(xs[i + 1 - window : i + 1]))
    return out


def volatility(xs: List[float], window: int) -> List[Optional[float]]:
    out: List[Optional[float]] = []
    for i in range(len(xs)):
        if i + 1 < window:
            out.append(None)
        else:
            chunk = xs[i + 1 - window : i + 1]
            mean = sum(chunk) / window
            var = sum((x - mean) ** 2 for x in chunk) / window
            out.append(math.sqrt(var))
    return out
