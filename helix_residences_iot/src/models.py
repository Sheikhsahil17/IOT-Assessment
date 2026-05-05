from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List


STATUS_SAFE = "Safe"
STATUS_WARNING = "Warning"
STATUS_DANGER = "Danger"


@dataclass(slots=True)
class ZoneConfig:
    name: str
    base_temperature: float
    base_humidity: float
    base_air_quality: float
    base_light_level: float
    vent_open_ratio: float


@dataclass(slots=True)
class SensorReading:
    timestamp: datetime
    zone: str
    temperature: float
    humidity: float
    air_quality: float
    light_level: float
    vent_open_ratio: float
    vent_state: str
    scenario: str = "normal"


@dataclass(slots=True)
class ZoneAssessment:
    zone: str
    timestamp: datetime
    status: str
    metric_states: Dict[str, str]
    breaches: List[str]
    recommendation: str


@dataclass(slots=True)
class AlertEvent:
    timestamp: datetime
    zone: str
    severity: str
    message: str
    recommendation: str
    alert_type: str
    scenario: str = "normal"


@dataclass(slots=True)
class ZoneSnapshot:
    reading: SensorReading
    assessment: ZoneAssessment
    recent_alerts: List[AlertEvent] = field(default_factory=list)
