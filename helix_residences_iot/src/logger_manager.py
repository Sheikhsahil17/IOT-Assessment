from __future__ import annotations

import csv
import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Iterable, List

from .models import AlertEvent, SensorReading
from .utils import ensure_directory, format_timestamp


class DataLogger:
    """Writes readings and alerts to CSV and JSON audit files."""

    def __init__(self, base_dir: Path) -> None:
        self.base_dir = base_dir
        self.data_dir = ensure_directory(base_dir / "data")
        self.export_dir = ensure_directory(self.data_dir / "exported")

        self.readings_csv = self.data_dir / "readings.csv"
        self.alerts_csv = self.data_dir / "alerts.csv"
        self.readings_json = self.data_dir / "readings.json"
        self.alerts_json = self.data_dir / "alerts.json"

        self._init_csv_files()

    def _init_csv_files(self) -> None:
        if not self.readings_csv.exists():
            with self.readings_csv.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                writer.writerow(
                    [
                        "timestamp",
                        "zone",
                        "temperature",
                        "humidity",
                        "air_quality",
                        "light_level",
                        "vent_open_ratio",
                        "vent_state",
                        "scenario",
                    ]
                )
        if not self.alerts_csv.exists():
            with self.alerts_csv.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                writer.writerow(
                    ["timestamp", "zone", "severity", "message", "recommendation", "alert_type", "scenario"]
                )

    def _append_json_record(self, path: Path, record: dict) -> None:
        existing: List[dict] = []
        if path.exists():
            try:
                existing = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                existing = []
        existing.append(record)
        path.write_text(json.dumps(existing, indent=2), encoding="utf-8")

    def log_reading(self, reading: SensorReading) -> None:
        with self.readings_csv.open("a", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(
                [
                    format_timestamp(reading.timestamp),
                    reading.zone,
                    reading.temperature,
                    reading.humidity,
                    reading.air_quality,
                    reading.light_level,
                    reading.vent_open_ratio,
                    reading.vent_state,
                    reading.scenario,
                ]
            )

        record = asdict(reading)
        record["timestamp"] = format_timestamp(reading.timestamp)
        self._append_json_record(self.readings_json, record)

    def log_alerts(self, alerts: Iterable[AlertEvent]) -> None:
        for alert in alerts:
            with self.alerts_csv.open("a", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                writer.writerow(
                    [
                        format_timestamp(alert.timestamp),
                        alert.zone,
                        alert.severity,
                        alert.message,
                        alert.recommendation,
                        alert.alert_type,
                        alert.scenario,
                    ]
                )
            record = asdict(alert)
            record["timestamp"] = format_timestamp(alert.timestamp)
            self._append_json_record(self.alerts_json, record)

    def reset_logs(self) -> None:
        for path in [self.readings_csv, self.alerts_csv, self.readings_json, self.alerts_json]:
            if path.exists():
                path.unlink()
        self._init_csv_files()
