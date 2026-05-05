from __future__ import annotations

from collections import Counter, defaultdict, deque
from typing import Deque, Dict, Iterable, List

from .models import AlertEvent, ZoneAssessment


class AlertManager:
    """Tracks alert history and repeated issue patterns."""

    def __init__(self, repeated_warning_count: int = 3) -> None:
        self.repeated_warning_count = repeated_warning_count
        self.zone_status_history: Dict[str, Deque[str]] = defaultdict(lambda: deque(maxlen=repeated_warning_count))
        self.alert_history: List[AlertEvent] = []

    def create_alert(
        self,
        assessment: ZoneAssessment,
        severity: str,
        message: str,
        recommendation: str,
        alert_type: str,
        scenario: str,
    ) -> AlertEvent:
        alert = AlertEvent(
            timestamp=assessment.timestamp,
            zone=assessment.zone,
            severity=severity,
            message=message,
            recommendation=recommendation,
            alert_type=alert_type,
            scenario=scenario,
        )
        self.alert_history.append(alert)
        return alert

    def process_assessment(self, assessment: ZoneAssessment, base_alerts: Iterable[tuple[str, str, str]], scenario: str) -> List[AlertEvent]:
        created: List[AlertEvent] = []
        history = self.zone_status_history[assessment.zone]
        history.append(assessment.status)

        for severity, alert_type, message in base_alerts:
            created.append(
                self.create_alert(
                    assessment,
                    severity,
                    message,
                    assessment.recommendation,
                    alert_type,
                    scenario,
                )
            )

        if len(history) == self.repeated_warning_count and all(status != "Safe" for status in history):
            created.append(
                self.create_alert(
                    assessment,
                    "Warning" if assessment.status == "Warning" else assessment.status,
                    f"{assessment.zone}: repeated non-safe environmental pattern detected.",
                    f"Schedule a facilities inspection for {assessment.zone} due to repeated comfort violations.",
                    "repeated_pattern",
                    scenario,
                )
            )
        return created

    def recent_alerts(self, limit: int = 10) -> List[AlertEvent]:
        return self.alert_history[-limit:]

    def alert_type_counts(self) -> Dict[str, int]:
        return dict(Counter(alert.alert_type for alert in self.alert_history))
