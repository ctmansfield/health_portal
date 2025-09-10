from __future__ import annotations
from typing import Optional, Tuple

# See docs/CONTINUE_BLOCK_01_UNITS.md
_SYNONYM = {
    "bpm": "1/min",
    "beat/min": "1/min",
    "beats/min": "1/min",
    "/min": "1/min",
    "%": "%",
    "percent": "%",
    "kg": "kg",
    "kilogram": "kg",
    "lb": "[lb_av]",
    "lbs": "[lb_av]",
    "pound": "[lb_av]",
    "mmhg": "mm[Hg]",
    "mm hg": "mm[Hg]",
    "c": "Cel",
    "cel": "Cel",
    "°c": "Cel",
    "f": "[degF]",
    "°f": "[degF]",
    "mg/dl": "mg/dL",
    "mmol/l": "mmol/L",
    "count": "{count}",
    "steps": "{count}",
    "step": "{count}",
}


def canonical_unit(u: Optional[str]) -> Optional[str]:
    if u is None:
        return None
    s = u.strip().lower()
    return _SYNONYM.get(s, u)


def convert(
    value: float, unit: Optional[str], target: Optional[str]
) -> Tuple[float, Optional[str]]:
    """
    Returns (converted_value, canonical_target_unit).
    If conversion unsupported but units are equivalent, returns input.
    If target is None, returns value with canonicalized input unit.
    """
    if unit is None and target is None:
        return value, None
    cu = canonical_unit(unit)
    ct = canonical_unit(target) if target else None
    # If no explicit target, just canonicalize the input unit
    if ct is None:
        return value, cu
    # Identity
    if cu == ct:
        return value, ct
    # Temperature conversion
    if cu == "[degF]" and ct == "Cel":
        return (value - 32.0) * (5.0 / 9.0), "Cel"
    if cu == "Cel" and ct == "[degF]":
        return (value * 9.0 / 5.0) + 32.0, "[degF]"
    # Weight conversion
    if cu == "[lb_av]" and ct == "kg":
        return value * 0.45359237, "kg"
    if cu == "kg" and ct == "[lb_av]":
        return value / 0.45359237, "[lb_av]"
    # SpO2 to fraction
    if cu in {"%", "percent"} and ct == "%":
        v = value
        if v > 1.0:
            v = v / 100.0
        return v, "%"
    # Heart rate already canonical as 1/min
    if cu == "1/min" and ct == "1/min":
        return value, "1/min"
    # Blood glucose mmol/L <-> mg/dL
    if cu == "mmol/L" and ct == "mg/dL":
        return value * 18.0182, "mg/dL"
    if cu == "mg/dL" and ct == "mmol/L":
        return value / 18.0182, "mmol/L"
    # BP mmHg canonical
    if cu == "mm[Hg]" and ct == "mm[Hg]":
        return value, "mm[Hg]"
    # Step/counts canonical
    if cu == "{count}" and ct == "{count}":
        return value, "{count}"
    # Fallback: no conversion rule found; return with canonical target
    return value, ct
