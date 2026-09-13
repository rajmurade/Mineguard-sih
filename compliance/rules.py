"""Rules loading + validation. The editable source of truth is ``rules.json``."""

from __future__ import annotations

import importlib.resources
import json
from pathlib import Path

from compliance.models import EventType, Severity

_THRESHOLD_EVENT_TYPES = {
    EventType.AQI_HIGH,
    EventType.GAS_HIGH,
    EventType.TEMP_HIGH,
    EventType.NOISE_HIGH,
    EventType.DUST_HIGH,
}


def load_rules() -> dict:
    """Load the packaged default rules (``compliance/rules.json``)."""
    with importlib.resources.files("compliance").joinpath("rules.json").open(
        encoding="utf-8"
    ) as fh:
        return json.load(fh)


def load_rules_from_path(path: str | Path) -> dict:
    with Path(path).open(encoding="utf-8") as fh:
        return json.load(fh)


def validate_rules(rules: dict) -> None:
    """Raise ValueError if the rules table is malformed."""
    if "debounce" not in rules:
        raise ValueError("rules missing 'debounce' section")
    for field in ("window_seconds", "required_detections"):
        if not isinstance(rules["debounce"].get(field), (int, float)) or rules["debounce"][field] <= 0:
            raise ValueError(f"debounce.{field} must be > 0")

    if "cv" not in rules:
        raise ValueError("rules missing 'cv' section")
    known_cv_types = {evt.value for evt in EventType if evt.is_cv}
    for name, rule in rules["cv"].items():
        if name not in known_cv_types:
            raise ValueError(f"unknown cv event type '{name}'")
        severity = rule.get("severity")
        if severity not in {sev.value for sev in Severity}:
            raise ValueError(f"cv rule '{name}' has invalid severity '{severity}'")
        if "confidence_min" in rule:
            if not isinstance(rule["confidence_min"], (int, float)):
                raise ValueError(f"cv rule '{name}'.confidence_min must be numeric")

    if "thresholds" not in rules:
        raise ValueError("rules missing 'thresholds' section")
    for name, bands in rules.get("thresholds", {}).items():
        if name not in {evt.value for evt in _THRESHOLD_EVENT_TYPES}:
            raise ValueError(f"unknown threshold event type '{name}'")
        if not bands or not isinstance(bands, list):
            raise ValueError(f"thresholds.{name} must be a non-empty list")
        for i, band in enumerate(bands):
            if not isinstance(band, dict) or "severity" not in band:
                raise ValueError(f"thresholds.{name}[{i}] must have 'severity'")
            if band["severity"] not in {sev.value for sev in Severity}:
                raise ValueError(f"thresholds.{name}[{i}] invalid severity")
            has_min = "min" in band
            has_max = "max" in band
            if i == len(bands) - 1:
                if has_max:
                    raise ValueError(
                        f"thresholds.{name}: only the last band may omit 'max'"
                    )
            elif not (has_min and has_max):
                raise ValueError(
                    f"thresholds.{name}[{i}] must define both 'min' and 'max'"
                )

    return None


DEFAULT_RULES = load_rules()