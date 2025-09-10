# Helper functions to normalize code systems and units for analytics

_SYSTEM_MAP = {
    "http://loinc.org": "LOINC",
    "http://snomed.info/sct": "SNOMED",
    "http://www.nlm.nih.gov/research/umls/rxnorm": "RxNorm",
    "http://www.whocc.no/atc": "ATC",
}


def normalize_system(url: str) -> str | None:
    """Map FHIR code system URLs to short names, else return the input."""
    return _SYSTEM_MAP.get(url, url)


_UNIT_MAP = {
    "kg": "kg",
    "[kg]": "kg",
    "g": "g",
    "cm": "cm",
    "mm": "mm",
    "m": "m",
    "L": "L",
    "l": "L",
    "ml": "mL",
    "mm[Hg]": "mm[Hg]",
    "mmHg": "mm[Hg]",
    "%": "%",
    "bpm": "beats/min",
    "/min": "beats/min",
    "beats/min": "beats/min",
    "°C": "°C",
    "Cel": "°C",
    "K": "K",
    "mg/dL": "mg/dL",
    "mmol/L": "mmol/L",
    "IU/L": "IU/L",
    "10*3/uL": "10^3/uL",
    "10^9/L": "10^9/L",
}


def normalize_unit(unit: str) -> str:
    """Map UCUM quirks to display/preferred units."""
    return _UNIT_MAP.get(unit, unit)
