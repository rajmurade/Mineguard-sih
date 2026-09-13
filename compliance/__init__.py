"""Compliance Engine — MineGuard.

Pure-Python decision logic decoupled from FastAPI/DB. The backend or the CV
pipeline calls :func:`evaluate_event` before writing an Incident row.
"""

from compliance.rules import DEFAULT_RULES, load_rules, load_rules_from_path
from compliance.engine import ComplianceEngine, evaluate_event
from compliance.models import ComplianceDecision, SafetyEvent, Severity


def create_engine(rules: dict | None = None, **kwargs) -> ComplianceEngine:
    """Build a fresh engine, optionally with custom rules or a custom clock."""
    return ComplianceEngine(rules=rules if rules is not None else DEFAULT_RULES, **kwargs)


__all__ = [
    "ComplianceDecision",
    "ComplianceEngine",
    "SafetyEvent",
    "Severity",
    "evaluate_event",
    "create_engine",
    "load_rules",
    "load_rules_from_path",
    "DEFAULT_RULES",
]