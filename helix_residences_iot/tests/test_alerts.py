import unittest
from datetime import datetime

from src.alerts import AlertManager
from src.models import ZoneAssessment


class AlertManagerTests(unittest.TestCase):
    def test_repeated_pattern_alert(self) -> None:
        manager = AlertManager(repeated_warning_count=3)
        created = []
        for _ in range(3):
            assessment = ZoneAssessment(
                zone="Co-working Space",
                timestamp=datetime.now(),
                status="Warning",
                metric_states={"air_quality": "Warning"},
                breaches=["air_quality"],
                recommendation="Increase airflow.",
            )
            created.extend(manager.process_assessment(assessment, [], "normal"))

        self.assertTrue(any(alert.alert_type == "repeated_pattern" for alert in created))


if __name__ == "__main__":
    unittest.main()
