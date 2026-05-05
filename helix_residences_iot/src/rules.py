from __future__ import annotations

from typing import Dict, List, Tuple

from .models import (
    STATUS_DANGER,
    STATUS_SAFE,
    STATUS_WARNING,
    SensorReading,
    ZoneAssessment,
)


class RuleEngine:
    """Applies threshold-based comfort and air quality rules."""

    def __init__(self, thresholds: Dict[str, Dict[str, float]]) -> None:
        self.thresholds = thresholds

    def _range_status(self, value: float, config: Dict[str, float]) -> str:
        safe_min = config.get("safe_min", float("-inf"))
        safe_max = config.get("safe_max", float("inf"))
        warning_min = config.get("warning_min", float("-inf"))
        warning_max = config.get("warning_max", float("inf"))

        if safe_min <= value <= safe_max:
            return STATUS_SAFE
        if warning_min <= value <= warning_max:
            return STATUS_WARNING
        return STATUS_DANGER

    def _max_only_status(self, value: float, config: Dict[str, float]) -> str:
        if value <= config["safe_max"]:
            return STATUS_SAFE
        if value <= config["warning_max"]:
            return STATUS_WARNING
        return STATUS_DANGER

    def _min_only_status(self, value: float, config: Dict[str, float]) -> str:
        if value >= config["safe_min"]:
            return STATUS_SAFE
        if value >= config["warning_min"]:
            return STATUS_WARNING
        return STATUS_DANGER

    def classify_metric_states(self, reading: SensorReading) -> Dict[str, str]:
        return {
            "temperature": self._range_status(reading.temperature, self.thresholds["temperature"]),
            "humidity": self._range_status(reading.humidity, self.thresholds["humidity"]),
            "air_quality": self._max_only_status(reading.air_quality, self.thresholds["air_quality"]),
            "light_level": self._min_only_status(reading.light_level, self.thresholds["light_level"]),
            "vent_open_ratio": self._range_status(
                reading.vent_open_ratio, self.thresholds["vent_open_ratio"]
            ),
        }

    def _recommendation_for_breaches(self, zone: str, breaches: List[str], scenario: str) -> str:
        if scenario == "ventilation_failure":
            return f"Inspect mechanical ventilation in {zone} and verify vent actuator state."
        if scenario == "sensor_fault":
            return f"Check sensor calibration and connectivity in {zone}; readings appear unreliable."
        if "air_quality" in breaches:
            return f"Increase airflow in {zone} and investigate occupancy-related air quality decline."
        if "temperature" in breaches and "humidity" in breaches:
            return f"Review HVAC performance in {zone} and schedule a facilities comfort inspection."
        if "light_level" in breaches:
            return f"Check lighting schedule and fixture status in {zone}."
        if "vent_open_ratio" in breaches:
            return f"Inspect window or vent position sensor in {zone}."
        return f"Continue monitoring {zone}; no immediate facilities action required."

    def assess(self, reading: SensorReading) -> ZoneAssessment:
        metric_states = self.classify_metric_states(reading)
        breaches = [metric for metric, status in metric_states.items() if status != STATUS_SAFE]

        overall_status = STATUS_SAFE
        if any(status == STATUS_DANGER for status in metric_states.values()):
            overall_status = STATUS_DANGER
        elif any(status == STATUS_WARNING for status in metric_states.values()):
            overall_status = STATUS_WARNING

        recommendation = self._recommendation_for_breaches(reading.zone, breaches, reading.scenario)
        return ZoneAssessment(
            zone=reading.zone,
            timestamp=reading.timestamp,
            status=overall_status,
            metric_states=metric_states,
            breaches=breaches,
            recommendation=recommendation,
        )

    def build_alerts(self, reading: SensorReading, assessment: ZoneAssessment) -> List[Tuple[str, str, str]]:
        alerts: List[Tuple[str, str, str]] = []
        for metric, status in assessment.metric_states.items():
            if status == STATUS_SAFE:
                continue
            message = f"{reading.zone}: {metric.replace('_', ' ')} is {status.lower()}."
            alerts.append((status, metric, message))
        return alerts
