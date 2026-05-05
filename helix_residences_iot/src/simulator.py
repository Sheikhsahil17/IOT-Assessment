from __future__ import annotations

import math
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from .models import SensorReading, ZoneConfig
from .utils import clamp


class EnvironmentalSimulator:
    """Generates realistic communal-area readings for Helix Residences."""

    def __init__(self, zones: List[ZoneConfig], seed: int, step_minutes: int) -> None:
        self.zones = {zone.name: zone for zone in zones}
        self.seed = seed
        self.step_minutes = step_minutes
        self.random = random.Random(seed)
        self.start_time = datetime(2026, 4, 1, 6, 0, 0)
        self.current_time = self.start_time
        self.step_count = 0
        self.active_scenarios: Dict[str, Optional[str]] = {zone.name: None for zone in zones}

    def reset(self) -> None:
        self.random = random.Random(self.seed)
        self.current_time = self.start_time
        self.step_count = 0
        self.active_scenarios = {zone: None for zone in self.zones}

    def set_scenario(self, zone: str, scenario: Optional[str]) -> None:
        self.active_scenarios[zone] = scenario

    def clear_scenarios(self) -> None:
        self.active_scenarios = {zone: None for zone in self.zones}

    def _occupancy_factor(self, zone: str, hour: int) -> float:
        if zone == "Gym":
            return 0.95 if hour in {7, 8, 18, 19, 20} else 0.4
        if zone == "Co-working Space":
            return 0.9 if 9 <= hour <= 17 else 0.15
        if zone == "Lobby":
            return 0.75 if 7 <= hour <= 9 or 17 <= hour <= 21 else 0.35
        if zone == "Corridor":
            return 0.5 if 6 <= hour <= 23 else 0.1
        if zone == "Rooftop Lounge":
            return 0.8 if 16 <= hour <= 22 else 0.2
        return 0.3

    def _daily_wave(self, hour: int, offset: float = 0.0) -> float:
        radians = ((hour + offset) / 24.0) * (2 * math.pi)
        return math.sin(radians)

    def _apply_scenario(self, zone: str, values: Dict[str, float]) -> Dict[str, float]:
        scenario = self.active_scenarios.get(zone)
        if scenario == "ventilation_failure":
            values["air_quality"] += 420
            values["humidity"] += 8
            values["vent_open_ratio"] = 0.02
        elif scenario == "overheating":
            values["temperature"] += 4.5
            values["humidity"] += 4
        elif scenario == "poor_air_quality":
            values["air_quality"] += 550
        elif scenario == "sensor_fault":
            values["temperature"] += self.random.choice([-8.0, 8.5])
            values["light_level"] += self.random.choice([-220.0, 260.0])
        elif scenario == "stuck_vent":
            values["vent_open_ratio"] = 1.0
        return values

    def generate_reading(self, zone_name: str) -> SensorReading:
        zone = self.zones[zone_name]
        hour = self.current_time.hour
        occupancy = self._occupancy_factor(zone.name, hour)
        drift = self._daily_wave(hour, offset=self.step_count * 0.1)

        values = {
            "temperature": zone.base_temperature + drift * 1.4 + occupancy * 1.6 + self.random.uniform(-0.4, 0.4),
            "humidity": zone.base_humidity + occupancy * 6.5 + self.random.uniform(-1.8, 1.8),
            "air_quality": zone.base_air_quality + occupancy * 260 + self.random.uniform(-35, 35),
            "light_level": zone.base_light_level + drift * 80 + self.random.uniform(-20, 20),
            "vent_open_ratio": clamp(
                zone.vent_open_ratio + self.random.uniform(-0.1, 0.1) + (0.1 if zone.name == "Lobby" and occupancy > 0.6 else 0.0),
                0.0,
                1.0,
            ),
        }

        if zone.name == "Gym":
            values["temperature"] += occupancy * 1.3
            values["humidity"] += occupancy * 5.0
        elif zone.name == "Co-working Space":
            values["air_quality"] += occupancy * 140
        elif zone.name == "Corridor" and (hour < 6 or hour > 22):
            values["light_level"] -= 110
        elif zone.name == "Rooftop Lounge":
            values["temperature"] += drift * 1.2
            values["light_level"] += 45

        values = self._apply_scenario(zone.name, values)

        vent_state = "Open" if values["vent_open_ratio"] >= 0.45 else "Partially Open" if values["vent_open_ratio"] >= 0.12 else "Closed"
        scenario = self.active_scenarios.get(zone.name) or "normal"

        return SensorReading(
            timestamp=self.current_time,
            zone=zone.name,
            temperature=round(values["temperature"], 2),
            humidity=round(clamp(values["humidity"], 18.0, 85.0), 2),
            air_quality=round(clamp(values["air_quality"], 350.0, 2200.0), 2),
            light_level=round(clamp(values["light_level"], 20.0, 900.0), 2),
            vent_open_ratio=round(values["vent_open_ratio"], 2),
            vent_state=vent_state,
            scenario=scenario,
        )

    def step(self) -> List[SensorReading]:
        readings = [self.generate_reading(zone_name) for zone_name in self.zones]
        self.current_time += timedelta(minutes=self.step_minutes)
        self.step_count += 1
        return readings
