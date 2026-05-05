import unittest

from src.config_loader import load_simulation_config, load_zone_configs
from src.simulator import EnvironmentalSimulator


class SimulatorTests(unittest.TestCase):
    def setUp(self) -> None:
        config = load_simulation_config()
        self.simulator = EnvironmentalSimulator(load_zone_configs(), config["seed"], config["step_minutes"])

    def test_step_generates_all_zones(self) -> None:
        readings = self.simulator.step()
        self.assertEqual(len(readings), 5)
        self.assertEqual({reading.zone for reading in readings}, {zone.name for zone in load_zone_configs()})

    def test_values_stay_within_expected_bounds(self) -> None:
        readings = self.simulator.step()
        for reading in readings:
            self.assertGreaterEqual(reading.temperature, 10.0)
            self.assertLessEqual(reading.temperature, 40.0)
            self.assertGreaterEqual(reading.humidity, 18.0)
            self.assertLessEqual(reading.humidity, 85.0)
            self.assertGreaterEqual(reading.air_quality, 350.0)
            self.assertLessEqual(reading.air_quality, 2200.0)

    def test_ventilation_failure_raises_air_quality(self) -> None:
        self.simulator.set_scenario("Gym", "ventilation_failure")
        readings = {reading.zone: reading for reading in self.simulator.step()}
        self.assertGreater(readings["Gym"].air_quality, 1100.0)


if __name__ == "__main__":
    unittest.main()
