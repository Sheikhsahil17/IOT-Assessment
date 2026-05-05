from __future__ import annotations

from collections import defaultdict
import os
from pathlib import Path
from statistics import mean
from typing import Dict, List, Sequence

MPL_CONFIG_DIR = Path(__file__).resolve().parents[1] / ".matplotlib"
MPL_CONFIG_DIR.mkdir(exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(MPL_CONFIG_DIR))

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt

from .models import AlertEvent, SensorReading, ZoneAssessment
from .utils import ensure_directory


class AnalyticsEngine:
    """Produces summary metrics and chart exports for the report and dashboard."""

    def __init__(self, base_dir: Path) -> None:
        self.chart_dir = ensure_directory(base_dir / "outputs" / "charts")

    def rolling_average(self, readings: Sequence[SensorReading], metric: str, window: int = 5) -> List[float]:
        values = [getattr(reading, metric) for reading in readings]
        averages: List[float] = []
        for index in range(len(values)):
            start = max(0, index - window + 1)
            averages.append(mean(values[start : index + 1]))
        return averages

    def zone_breach_counts(self, assessments: Sequence[ZoneAssessment]) -> Dict[str, int]:
        counts: Dict[str, int] = defaultdict(int)
        for assessment in assessments:
            if assessment.status != "Safe":
                counts[assessment.zone] += 1
        return dict(counts)

    def worst_performing_zone(self, assessments: Sequence[ZoneAssessment]) -> str:
        counts = self.zone_breach_counts(assessments)
        return max(counts, key=counts.get) if counts else "No issues recorded"

    def most_frequent_alert_type(self, alerts: Sequence[AlertEvent]) -> str:
        if not alerts:
            return "No alerts recorded"
        counts: Dict[str, int] = defaultdict(int)
        for alert in alerts:
            counts[alert.alert_type] += 1
        return max(counts, key=counts.get)

    def export_zone_chart(self, zone: str, readings: Sequence[SensorReading], metric: str) -> Path:
        timestamps = [reading.timestamp.strftime("%H:%M") for reading in readings]
        values = [getattr(reading, metric) for reading in readings]
        smoothed = self.rolling_average(readings, metric)

        figure, axis = plt.subplots(figsize=(8, 4))
        axis.plot(timestamps, values, label=metric.replace("_", " ").title(), color="#1f77b4", linewidth=2)
        axis.plot(timestamps, smoothed, label="Rolling average", color="#ff7f0e", linestyle="--")
        axis.set_title(f"{zone} {metric.replace('_', ' ').title()} Trend")
        axis.set_xlabel("Time")
        axis.set_ylabel(metric.replace("_", " ").title())
        axis.tick_params(axis="x", rotation=45)
        axis.grid(alpha=0.25)
        axis.legend()
        figure.tight_layout()

        path = self.chart_dir / f"{zone.lower().replace(' ', '_')}_{metric}.png"
        figure.savefig(path, dpi=160)
        plt.close(figure)
        return path
