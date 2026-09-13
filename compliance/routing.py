"""Alert routing per severity level — pure config + lookup."""

from __future__ import annotations

from compliance.models import Severity

# Keep keys aligned with Severity values. Routing is also applied to the
# not-yet-confirmed debounce decisions by other modules via lookup_severity.
ROUTING_TABLE: dict[str, dict] = {
    "compliant": {"recipients": [], "escalate_external": False},
    "warning": {"recipients": ["affected_worker", "local_supervisor"], "escalate_external": False},
    "high": {"recipients": ["safety_officer", "site_manager"], "escalate_external": False},
    "critical": {"recipients": ["safety_officer", "site_manager"], "escalate_external": True},
}


def recipients_for(severity: Severity) -> list[str]:
    entry = ROUTING_TABLE.get(severity.value, ROUTING_TABLE["compliant"])
    return list(entry["recipients"])


def escalate_external(severity: Severity) -> bool:
    entry = ROUTING_TABLE.get(severity.value, ROUTING_TABLE["compliant"])
    return bool(entry["escalate_external"])