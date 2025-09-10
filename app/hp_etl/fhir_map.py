from datetime import datetime, timezone
from typing import Optional
from app.hp_etl.units import convert, canonical_unit

LOINC_HR = "8867-4"
LOINC_SPO2 = "59408-5"


def _now_isoz():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def observation_to_event(obs: dict) -> Optional[dict]:
    """Turn valid FHIR Observation into normalized event dict or None."""
    if not isinstance(obs, dict):
        return None
    if obs.get("resourceType") != "Observation":
        return None
    coding = (obs.get("code") or {}).get("coding") or []
    if not coding:
        return None
    first_code = coding[0]
    system = first_code.get("system")
    code = first_code.get("code")
    display = first_code.get("display")
    if not (system and code):
        return None

    effective_time = (
        obs.get("effectiveDateTime")
        or obs.get("issued")
        or (obs.get("meta") or {}).get("lastUpdated")
        or _now_isoz()
    )

    value = None
    unit = None
    if "valueQuantity" in obs:
        q = obs["valueQuantity"]
        value = q.get("value")
        unit_in = q.get("unit")
        if code == LOINC_HR:
            value, unit = convert(value, unit_in, "1/min")
        elif code == LOINC_SPO2:
            value, unit = convert(value, unit_in, "%")
        else:
            value, unit = value, canonical_unit(unit_in)
    else:
        return None

    if value is None or not isinstance(value, (int, float)):
        return None

    code_system = "LOINC" if system and system.lower().endswith("loinc.org") else system

    return {
        "person_id": "me",
        "effective_time": (
            effective_time if effective_time.endswith("Z") else effective_time + "Z"
        ),
        "code_system": code_system,
        "code": code,
        "value_num": float(value),
        "unit": unit,
        "meta": {"source": "fhir"},
    }
