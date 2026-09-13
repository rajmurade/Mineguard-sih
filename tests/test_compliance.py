"""Unit tests for the MineGuard Compliance Engine."""

from datetime import datetime, timedelta

import pytest

from compliance.engine import ComplianceEngine, evaluate_event
from compliance.models import ComplianceDecision, Severity
from compliance.rules import load_rules_from_path, validate_rules
from compliance.debounce import DebounceTracker

T0 = datetime(2026, 1, 1, 8, 0, 0)


def env_event(event_type, value, ts=None):
    return {
        "source": "environmental",
        "event_type": event_type,
        "zone": "Zone A - Tunnel 1",
        "worker_id": None,
        "value": value,
        "timestamp": ts or T0,
    }


def cv_event(event_type, confidence=0.9, zone="Zone A - Tunnel 1", worker_id=1, ts=None, objects=None):
    event = {
        "source": "cv",
        "event_type": event_type,
        "zone": zone,
        "worker_id": worker_id,
        "confidence": confidence,
        "timestamp": ts or T0,
    }
    if objects is not None:
        event["objects"] = objects
    return event


# ----------------------------------------------------------------------
# Environmental severity tiers
# ----------------------------------------------------------------------


@pytest.mark.parametrize(
    "value,expected",
    [
        (100, "compliant"),
        (149, "compliant"),
        (150, "warning"),
        (300, "warning"),
        (301, "high"),
        (500, "high"),
        (501, "critical"),
    ],
)
def test_aqi_tiers(value, expected):
    decision = ComplianceEngine().evaluate(env_event("aqi_high", value))
    assert decision.severity.value == expected
    assert decision.should_create_incident == (expected != "compliant")


@pytest.mark.parametrize(
    "value,expected",
    [
        (39, "compliant"),
        (40, "warning"),
        (45, "warning"),
        (46, "high"),
        (50, "high"),
        (51, "critical"),
        (60, "critical"),
    ],
)
def test_temperature_tiers(value, expected):
    decision = ComplianceEngine().evaluate(env_event("temp_high", value))
    assert decision.severity.value == expected


@pytest.mark.parametrize(
    "value,expected",
    [
        (20, "compliant"),
        (50, "warning"),
        (160, "high"),
        (400, "critical"),
    ],
)
def test_gas_tiers(value, expected):
    decision = ComplianceEngine().evaluate(env_event("gas_high", value))
    assert decision.severity.value == expected


def test_noise_and_dust_tiers_are_expected_categories():
    engine = ComplianceEngine()
    assert engine.evaluate(env_event("noise_high", 90)).severity is Severity.WARNING
    assert engine.evaluate(env_event("noise_high", 120)).severity is Severity.CRITICAL
    assert engine.evaluate(env_event("dust_high", 2.5)).severity is Severity.WARNING
    assert engine.evaluate(env_event("dust_high", 5.5)).severity is Severity.CRITICAL


def test_compliant_environmental_creates_no_incident_and_no_recipients():
    decision = ComplianceEngine().evaluate(env_event("aqi_high", 100))
    assert decision.should_create_incident is False
    assert decision.alert_recipients == []


# ----------------------------------------------------------------------
# CV static rules (fire / restricted zone always critical)
# ----------------------------------------------------------------------


def _fire_trigger(engine, ts=None):
    """Return the 3rd consecutive detection decision (triggers incident)."""
    event = cv_event("fire", ts=ts or T0)
    engine.evaluate(event)
    engine.evaluate(cv_event("fire", ts=(ts or T0) + timedelta(seconds=1)))
    return engine.evaluate(cv_event("fire", ts=(ts or T0) + timedelta(seconds=2)))


def test_fire_always_critical():
    engine = ComplianceEngine()
    decision = _fire_trigger(engine)
    assert decision.should_create_incident is True
    assert decision.severity is Severity.CRITICAL
    assert decision.escalate_external is True


def test_restricted_zone_entry_always_critical():
    engine = ComplianceEngine()
    for i in range(3):
        decision = engine.evaluate(cv_event("restricted_zone_entry", ts=T0 + timedelta(seconds=i)))
    assert decision.severity is Severity.CRITICAL
    assert decision.should_create_incident is True


def test_smoke_and_fall_default_high():
    engine = ComplianceEngine()
    for i in range(3):
        engine.evaluate(cv_event("smoke", ts=T0 + timedelta(seconds=i)))
    smoke = engine.evaluate(cv_event("smoke", ts=T0 + timedelta(seconds=3)))
    assert smoke.severity is Severity.HIGH
    for i in range(4):
        engine.evaluate(cv_event("fall", ts=T0 + timedelta(seconds=i)))
    assert engine.evaluate(cv_event("fall", ts=T0 + timedelta(seconds=4))).severity is Severity.HIGH


# ----------------------------------------------------------------------
# confidence gate
# ----------------------------------------------------------------------


def test_no_helmet_high_after_confirmation():
    engine = ComplianceEngine()
    for i in range(3):
        decision = engine.evaluate(cv_event("no_helmet", confidence=0.95, ts=T0 + timedelta(seconds=i)))
    assert decision.severity is Severity.HIGH
    assert decision.should_create_incident is True
    assert decision.alert_recipients == ["safety_officer", "site_manager"]


def test_no_helmet_ignored_when_confidence_below_minimum():
    engine = ComplianceEngine()
    decisions = [
        engine.evaluate(cv_event("no_helmet", confidence=0.55, ts=T0 + timedelta(seconds=i)))
        for i in range(10)
    ]
    assert all(d.should_create_incident is False for d in decisions)
    assert all(d.severity is Severity.COMPLIANT for d in decisions)
    assert all("confidence" in d.reason for d in decisions)


def test_no_helmet_low_confidence_does_not_count_towards_debounce():
    engine = ComplianceEngine()
    engine.evaluate(cv_event("no_helmet", confidence=0.5, ts=T0))
    engine.evaluate(cv_event("no_helmet", confidence=0.5, ts=T0 + timedelta(seconds=1)))
    decision = engine.evaluate(cv_event("no_helmet", confidence=0.5, ts=T0 + timedelta(seconds=2)))
    assert decision.should_create_incident is False
    assert decision.severity is Severity.COMPLIANT


# ----------------------------------------------------------------------
# proximity_risk combo rule
# ----------------------------------------------------------------------


def test_proximity_risk_high_by_default():
    engine = ComplianceEngine()
    for i in range(3):
        decision = engine.evaluate(cv_event("proximity_risk", ts=T0 + timedelta(seconds=i)))
    assert decision.severity is Severity.HIGH
    assert decision.escalate_external is False


def test_proximity_risk_critical_with_worker_heavy_vehicle_combo():
    engine = ComplianceEngine()
    for i in range(3):
        decision = engine.evaluate(
            cv_event(
                "proximity_risk",
                zone="Zone B - Open Pit",
                worker_id=7,
                ts=T0 + timedelta(seconds=i),
                objects=["worker", "heavy_vehicle"],
            )
        )
    assert decision.severity is Severity.CRITICAL
    assert decision.escalate_external is True


def test_proximity_risk_does_not_critical_without_vehicle():
    engine = ComplianceEngine()
    for i in range(3):
        decision = engine.evaluate(
            cv_event("proximity_risk", ts=T0 + timedelta(seconds=i), objects=["worker", "truck"])
        )
    assert decision.severity is Severity.HIGH


# ----------------------------------------------------------------------
# debounce logic
# ----------------------------------------------------------------------


def test_cv_requires_three_detections_within_window():
    engine = ComplianceEngine()
    d1 = engine.evaluate(cv_event("fall", ts=T0))
    d2 = engine.evaluate(cv_event("fall", ts=T0 + timedelta(seconds=1)))
    d3 = engine.evaluate(cv_event("fall", ts=T0 + timedelta(seconds=2)))

    assert d1.should_create_incident is False
    assert d2.should_create_incident is False
    assert d3.should_create_incident is True
    assert "3/3" in d3.reason


def test_debounce_window_expiry_resets_counter():
    engine = ComplianceEngine()
    engine.evaluate(cv_event("fall", ts=T0))
    engine.evaluate(cv_event("fall", ts=T0 + timedelta(seconds=1)))
    # gap of 6s exceeds the 5s window -> streak resets
    d = engine.evaluate(cv_event("fall", ts=T0 + timedelta(seconds=7)))
    assert d.should_create_incident is False
    assert "1/3" in d.reason


def test_debounce_sliding_window_recounts():
    engine = ComplianceEngine()
    engine.evaluate(cv_event("fall", ts=T0))                            # count 1
    engine.evaluate(cv_event("fall", ts=T0 + timedelta(seconds=1)))     # count 2
    assert engine.evaluate(cv_event("fall", ts=T0 + timedelta(seconds=2))).should_create_incident  # count 3 -> fires

    # Old detections fall out of the 5s window; a fresh streak builds again.
    late = T0 + timedelta(seconds=30)
    assert engine.evaluate(cv_event("fall", ts=late)).should_create_incident is False            # 1
    assert engine.evaluate(cv_event("fall", ts=late + timedelta(seconds=1))).should_create_incident is False  # 2
    assert engine.evaluate(cv_event("fall", ts=late + timedelta(seconds=2))).should_create_incident is True  # 3


def test_engine_fires_once_per_streak():
    engine = ComplianceEngine()
    fired_at = [
        i
        for i in range(8)
        if engine.evaluate(cv_event("no_helmet", ts=T0 + timedelta(seconds=i))).should_create_incident
    ]
    # only the third detection (index 2) fires; keep-alive frames stay quiet
    assert fired_at == [2]
    assert "already confirmed" in engine.evaluate(
        cv_event("no_helmet", ts=T0 + timedelta(seconds=3))
    ).reason

    # after the streak fully expires, a fresh streak fires again
    new = T0 + timedelta(seconds=60)
    decisions = [
        engine.evaluate(cv_event("no_helmet", ts=new + timedelta(seconds=t))).should_create_incident
        for t in (0, 1, 2)
    ]
    assert decisions == [False, False, True]


def test_debounce_rising_edge_only():
    tracker = DebounceTracker(required_detections=3, window_seconds=5.0)
    key = ("no_helmet", "Zone A - Tunnel 1", 1)
    flags = [tracker.update(key, T0 + timedelta(seconds=i)) for i in range(6)]
    assert flags == [False, False, True, False, False, False]
    assert tracker.is_confirmed(key) is True

def test_debounce_keys_are_isolated():
    engine = ComplianceEngine()
    engine.evaluate(cv_event("fall", worker_id=1, ts=T0))
    engine.evaluate(cv_event("fall", worker_id=2, ts=T0))
    d = engine.evaluate(cv_event("fall", worker_id=2, ts=T0 + timedelta(seconds=1)))
    assert d.should_create_incident is False  # worker 2 only has 2
    d = engine.evaluate(cv_event("fall", worker_id=2, ts=T0 + timedelta(seconds=2)))
    assert d.should_create_incident is True

def test_debounce_not_applied_to_environmental():
    engine = ComplianceEngine()
    d = engine.evaluate(env_event("aqi_high", 600))
    assert d.should_create_incident is True


# ----------------------------------------------------------------------
# routing
# ----------------------------------------------------------------------


def test_warning_routes_to_worker_and_local_supervisor():
    decision = ComplianceEngine().evaluate(env_event("aqi_high", 200))
    assert decision.alert_recipients == ["affected_worker", "local_supervisor"]
    assert decision.escalate_external is False


def test_high_routes_to_safety_officer_and_site_manager():
    engine = ComplianceEngine()
    for i in range(3):
        decision = engine.evaluate(cv_event("no_helmet", ts=T0 + timedelta(seconds=i)))
    assert decision.alert_recipients == ["safety_officer", "site_manager"]
    assert decision.escalate_external is False


def test_critical_routes_to_safety_officer_site_manager_and_escalates_externally():
    engine = ComplianceEngine()
    for i in range(3):
        decision = engine.evaluate(cv_event("fire", ts=T0 + timedelta(seconds=i)))
    assert decision.alert_recipients == ["safety_officer", "site_manager"]
    assert decision.escalate_external is True


# ----------------------------------------------------------------------
# input validation / error handling
# ----------------------------------------------------------------------


def test_environmental_event_requires_value():
    with pytest.raises(ValueError, match="requires 'value'"):
        ComplianceEngine().evaluate(env_event("aqi_high", None))


def test_missing_required_field_raises():
    with pytest.raises(ValueError, match="missing required fields"):
        ComplianceEngine().evaluate({"source": "cv", "event_type": "fire"})


def test_unknown_event_type_raises():
    with pytest.raises(ValueError):
        ComplianceEngine().evaluate(cv_event("ufo_sighting"))


def test_unknown_source_raises():
    with pytest.raises(ValueError):
        ComplianceEngine().evaluate(
            {"source": "radar", "event_type": "fire", "zone": "Z", "timestamp": T0, "worker_id": None}
        )


def test_invalid_rules_rejected():
    bad = dict(load_rules_from_path("compliance/rules.json"))
    bad["cv"]["fire"]["severity"] = "nuclear"
    with pytest.raises(ValueError, match="invalid severity"):
        validate_rules(bad)


def test_decision_as_dict_shape():
    engine = ComplianceEngine()
    decision = engine.evaluate(env_event("temp_high", 42))
    payload = decision.as_dict()
    assert set(payload) == {
        "should_create_incident",
        "severity",
        "alert_recipients",
        "escalate_external",
        "reason",
    }
    assert isinstance(decision, ComplianceDecision)


def test_module_level_evaluate_event_entrypoint():
    event = env_event("aqi_high", 200)
    decision = evaluate_event(event)
    assert isinstance(decision, ComplianceDecision)
    assert decision.severity is Severity.WARNING