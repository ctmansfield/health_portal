import statistics
from typing import List, Tuple


def rolling_zscore(
    series: List[Tuple[str, float]], window: int = 21
) -> List[Tuple[str, float]]:
    """
    Compute the rolling z-score for each point based on trailing window (including current).
    Args:
        series: List of (iso_date, value), must be sorted by iso_date ascending.
        window: Days in the rolling window.
    Returns:
        List of (iso_date, zscore) with None for first points until window filled.
    """
    result = []
    vals = [v for _, v in series]
    for i in range(len(series)):
        istart = max(0, i - window + 1)
        win = vals[istart : i + 1]
        if len(win) < 2:
            result.append((series[i][0], 0.0))
        else:
            mean = statistics.mean(win)
            stdev = statistics.stdev(win)
            val = vals[i]
            score = (val - mean) / stdev if stdev > 1e-7 else 0.0
            result.append((series[i][0], score))
    return result


def level_from_score(score: float) -> str:
    abs_score = abs(score)
    if abs_score >= 3:
        return "alert"
    if abs_score >= 2:
        return "warn"
    return "info"
