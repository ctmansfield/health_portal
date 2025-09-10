from typing import Tuple, List


def validate_observation(obs: dict) -> Tuple[bool, List[str]]:
    errors = []
    if not isinstance(obs, dict):
        errors.append("Input is not a dict.")
        return False, errors

    if obs.get("resourceType") != "Observation":
        errors.append("resourceType is not 'Observation'.")

    code = obs.get("code")
    if not isinstance(code, dict) or "coding" not in code or not code["coding"]:
        errors.append("Observation.code.coding[0] missing.")
    else:
        coding0 = code["coding"][0]
        if "system" not in coding0 or not coding0["system"]:
            errors.append("Observation.code.coding[0].system missing.")
        if "code" not in coding0 or not coding0["code"]:
            errors.append("Observation.code.coding[0].code missing.")

    q = obs.get("valueQuantity")
    if (
        not isinstance(q, dict)
        or "value" not in q
        or not isinstance(q["value"], (int, float))
    ):
        errors.append("Observation.valueQuantity.value missing or not a number.")

    return (len(errors) == 0), errors
