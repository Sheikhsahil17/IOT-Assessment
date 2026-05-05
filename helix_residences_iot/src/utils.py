from __future__ import annotations

from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Deque, Iterable, TypeVar


T = TypeVar("T")


def ensure_directory(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def format_timestamp(timestamp: datetime) -> str:
    return timestamp.strftime("%Y-%m-%d %H:%M:%S")


def clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def rolling_window(items: Iterable[T], size: int) -> Deque[T]:
    window: Deque[T] = deque(maxlen=size)
    for item in items:
        window.append(item)
    return window
