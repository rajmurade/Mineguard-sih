import enum


class EntryExitDirection(str, enum.Enum):
    entry = "entry"
    exit = "exit"


class IncidentType(str, enum.Enum):
    ppe_violation = "ppe_violation"
    proximity_risk = "proximity_risk"
    fire_smoke = "fire_smoke"
    environmental = "environmental"
    unauthorized_zone = "unauthorized_zone"
    fall = "fall"


class Severity(str, enum.Enum):
    compliant = "compliant"
    warning = "warning"
    high = "high"
    critical = "critical"

    @classmethod
    def rank(cls, severity) -> int:
        order = [cls.compliant, cls.warning, cls.high, cls.critical]
        return order.index(cls(severity))

    @classmethod
    def meets_threshold(cls, severity, threshold: str) -> bool:
        return cls.rank(severity) >= cls.rank(threshold)


class ResolutionStatus(str, enum.Enum):
    open = "open"
    acknowledged = "acknowledged"
    resolved = "resolved"


class DataSource(str, enum.Enum):
    simulated = "simulated"
    real = "real"