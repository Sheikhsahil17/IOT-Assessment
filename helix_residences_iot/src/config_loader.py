from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from .models import ZoneConfig


BASE_DIR = Path(__file__).resolve().parents[1]


def load_json(relative_path: str) -> Dict[str, Any]:
    path = BASE_DIR / relative_path
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_thresholds() -> Dict[str, Any]:
    return load_json("config/thresholds.json")


def load_simulation_config() -> Dict[str, Any]:
    return load_json("config/simulation_config.json")


def load_zone_configs() -> List[ZoneConfig]:
    config = load_simulation_config()
    return [ZoneConfig(**zone_data) for zone_data in config["zones"]]
