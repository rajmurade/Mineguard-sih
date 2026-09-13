"""Core compliance evaluation logic — no DB, no framework."""

from __future__ import annotations

from datetime import datetime
from typing import Callable

from compliance.debounce import DebounceTracker
from compliance.models import (
    ComplianceDecision,
    EventType,
    SafetyEvent,
    Severity,
    Source,
)
from compliance.rules import DEFAULT_RULES, validate_rules
from compliance.routing import escalate_external, recipients_for


class ComplianceEngine:
    """Stateful engine holding rules + a CV debounce tracker.

    Use :meth:`evaluate` for a single event. A module-level convenience
    function :func:`evaluate_event` delegates to a default singleton.
    """

    def __init__(
        self,
        rules: dict | None = None,
        now_fn: Callable[[], datetime] | None = None,
    ) -> None:
        self.rules = rules if rules is not None else DEFAULT_RULES
        validate_rules(self.rules)
        debounce_cfg = self.rules["debounce"]
        self._debounce = DebounceTracker(
            required_detections=debounce_cfg["required_detections"],
            window_seconds=debounce_cfg["window_seconds"],
        )
        self._now_fn = now_fn or datetime.now

    # ------------------------------------------------------------------
    # public API
    # ------------------------------------------------------------------

    def evaluate(self, event: dict) -> ComplianceDecision:
        """Evaluate a normalized event dict and return a compliance decision."""
        ev = SafetyEvent.from_dict(event)
        now = ev.timestamp
        if ev.source is Source.CV:
            return self._evaluate_cv(ev, now)
        return self._evaluate_environmental(ev, now)

    # ------------------------------------------------------------------
    # CV evaluation
    # ------------------------------------------------------------------

    def _evaluate_cv(self, ev: SafetyEvent, now: datetime) -> ComplianceDecision:
        rule = self.rules["cv"].get(ev.event_type.value)
        if rule is None:
            return ComplianceDecision(
                should_create_incident=False,
                severity=Severity.COMPLIANT,
                alert_recipients=[],
                reason=f"no rule configured for cv event '{ev.event_type.value}'",
            )

        severity = Severity(rule["severity"])

        # --- confidence gate (only for rules that define one) ---------------
        confidence_min = rule.get("confidence_min")
        if confidence_min is not None:
            conf = ev.confidence or 0.0
            if conf < confidence_min:
                return ComplianceDecision(
                    should_create_incident=False,
                    severity=Severity.COMPLIANT,
                    alert_recipients=[],
                    reason=(
                        f"confidence {conf:.2f} below minimum {confidence_min:.2f} "
                        f"for {ev.event_type.value}; detection ignored"
                    ),
                )

        # --- combo escalation (e.g. proximity_risk + heavy vehicle) --------
        critical_combo = rule.get("critical_combo")
        if critical_combo and ev.objects:
            combo_set = set(ev.objects)
            if all(label in combo_set for label in critical_combo):
                severity = Severity.CRITICAL

        # --- debounce gate (CV events) ------------------------------------
        key = (ev.event_type.value, ev.zone, ev.worker_id)
        triggered = self._debounce.update(key, now)
        window = self._debounce.window_seconds
        required = self._debounce.required_detections
        count = self._debounce.current_count(key)

        if not triggered:
            if self._debounce.is_confirmed(key):
                reason = f"{ev.event_type.value}: already confirmed; no new incident"
            else:
                reason = (
                    f"{ev.event_type.value}: {count}/{required} detections within "
                    f"{window:.1f}s window; awaiting confirmation"
                )
            return ComplianceDecision(
                should_create_incident=False,
                severity=severity,
                alert_recipients=[],
                reason=reason,
            )

        return ComplianceDecision(
            should_create_incident=True,
            severity=severity,
            alert_recipients=recipients_for(severity),
            escalate_external=escalate_external(severity),
            reason=(
                f"{ev.event_type.value} confirmed: {count}/{required} detections "
                f"within {window:.1f}s window"
                + (f"; worker+vehicle combo detected" if critical_combo and ev.objects else "")
            ),
        )

    # ------------------------------------------------------------------
    # Environmental evaluation
    # ------------------------------------------------------------------

    def _evaluate_environmental(self, ev: SafetyEvent, _now: datetime) -> ComplianceDecision:
        bands = self.rules["thresholds"].get(ev.event_type.value)
        if bands is None:
            return ComplianceDecision(
                should_create_incident=False,
                severity=Severity.COMPLIANT,
                alert_recipients=[],
                reason=f"no rule configured for environmental event '{ev.event_type.value}'",
            )

        severity = self._classify(ev.value, bands)

        if severity is Severity.COMPLIANT:
            return ComplianceDecision(
                should_create_incident=False,
                severity=severity,
                alert_recipients=[],
                reason=f"{ev.event_type.value}: {ev.value} within normal range",
            )

        return ComplianceDecision(
            should_create_incident=True,
            severity=severity,
            alert_recipients=recipients_for(severity),
            escalate_external=escalate_external(severity),
            reason=(
                f"{ev.event_type.value}: {ev.value} triggered {severity.value} threshold"
            ),
        )

    @staticmethod
    def _classify(value: float, bands: list[dict]) -> Severity:
        for band in bands:
            if "max" not in band:
                return Severity(band["severity"])
            low = band.get("min", float("-inf"))
            if low <= value <= band["max"]:
                return Severity(band["severity"])
        return Severity(bands[-1]["severity"])


# ------------------------------------------------------------------
# Module-level convenience
# ------------------------------------------------------------------

_DEFAULT_ENGINE: ComplianceEngine | None = None


def _get_default_engine() -> ComplianceEngine:
    global _DEFAULT_ENGINE
    if _DEFAULT_ENGINE is None:
        _DEFAULT_ENGINE = ComplianceEngine()
    return _DEFAULT_ENGINE


def evaluate_event(event: dict) -> ComplianceDecision:
    """Main entry point. Evaluates an event dict against the default rules."""
    return _get_default_engine().evaluate(event)