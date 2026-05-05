import unittest
from datetime import datetime

from src.config_loader import load_thresholds
from src.models import STATUS_DANGER, STATUS_SAFE, STATUS_WARNING, SensorReading
from src.rules import RuleEngine


class RuleEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = RuleEngine(load_thresholds())

    def test_safe_reading_classification(self) -> None:
        reading = SensorReading(
            timestamp=datetime.now(),
            zone="Lobby",
            temperature=21.0,
            humidity=45.0,
            air_quality=700.0,
            light_level=320.0,
            vent_open_ratio=0.35,
            vent_state="Partially Open",
        )
        assessment = self.engine.assess(reading)
        self.assertEqual(assessment.status, STATUS_SAFE)

    def test_danger_air_quality_classification(self) -> None:
        reading = SensorReading(
            timestamp=datetime.now(),
            zone="Gym",
            temperature=22.0,
            humidity=50.0,
            air_quality=1500.0,
            light_level=400.0,
            vent_open_ratio=0.3,
            vent_state="Partially Open",
        )
        assessment = self.engine.assess(reading)
        self.assertEqual(assessment.metric_states["air_quality"], STATUS_DANGER)
        self.assertEqual(assessment.status, STATUS_DANGER)

    def test_warning_light_level(self) -> None:
        reading = SensorReading(
            timestamp=datetime.now(),
            zone="Corridor",
            temperature=20.0,
            humidity=42.0,
            air_quality=650.0,
            light_level=180.0,
            vent_open_ratio=0.2,
            vent_state="Partially Open",
        )
        assessment = self.engine.assess(reading)
        self.assertEqual(assessment.metric_states["light_level"], STATUS_WARNING)


if __name__ == "__main__":
    unittest.main()
