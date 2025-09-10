from dataclasses import dataclass
from typing import Optional, List


@dataclass
class MetricPoint:
    ts: str
    v: Optional[float]


def evaluate_rules(
    rules: List[dict], series_by_metric: dict[str, List[MetricPoint]]
) -> List[dict]:
    results = []
    for rule in rules:
        rid = rule["id"]
        cond = rule["when"]
        metric = cond.get("metric")
        op = cond.get("op")
        threshold = cond.get("value")
        level = rule.get("level")
        message = rule.get("message", "")

        series = series_by_metric.get(metric, [])
        # find latest non-null value by timestamp order descending
        latest_point = None
        for pt in reversed(series):
            if pt.v is not None:
                latest_point = pt
                break
        if latest_point is None:
            continue

        value = latest_point.v
        ts = latest_point.ts

        # Evaluate op
        match op:
            case "==":
                passed = value == threshold
            case "!=":
                passed = value != threshold
            case "<":
                passed = value < threshold
            case "<=":
                passed = value <= threshold
            case ">":
                passed = value > threshold
            case ">=":
                passed = value >= threshold
            case _:
                continue

        if passed:
            results.append(
                {
                    "rule_id": rid,
                    "metric": metric,
                    "level": level,
                    "message": message,
                    "at": ts,
                    "value": value,
                    "op": op,
                    "threshold": threshold,
                }
            )

    return results
