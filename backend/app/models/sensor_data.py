"""Validated sensor-reading schema shared by ingestion components."""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Mapping


@dataclass(frozen=True)
class SensorReading:
    device_id: str
    timestamp: str
    latitude: float
    longitude: float
    bme_gas: float
    mq135: float
    mq136: float
    mq3: float
    temperature: float
    humidity: float
    pressure: float
    is_simulated: bool

    def __post_init__(self) -> None:
        if not self.device_id.strip() or len(self.device_id) > 64:
            raise ValueError("device_id must contain 1-64 characters")
        if any(char in self.device_id for char in ".#$[]/"):
            raise ValueError("device_id contains a character not allowed in Firebase keys")

        try:
            parsed_timestamp = datetime.fromisoformat(self.timestamp.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("timestamp must be a valid ISO-8601 value") from exc
        if parsed_timestamp.tzinfo is None:
            raise ValueError("timestamp must include a timezone")

        ranges = {
            "latitude": (-90.0, 90.0),
            "longitude": (-180.0, 180.0),
            "bme_gas": (0.0, 10_000_000.0),
            "mq135": (0.0, 4095.0),
            "mq136": (0.0, 4095.0),
            "mq3": (0.0, 4095.0),
            "temperature": (-40.0, 85.0),
            "humidity": (0.0, 100.0),
            "pressure": (300.0, 1100.0),
        }
        for field_name, (minimum, maximum) in ranges.items():
            value = getattr(self, field_name)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ValueError(f"{field_name} must be a finite number")
            if not minimum <= float(value) <= maximum:
                raise ValueError(f"{field_name} must be between {minimum} and {maximum}")
        if not isinstance(self.is_simulated, bool):
            raise ValueError("is_simulated must be a boolean")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "SensorReading":
        required_fields = {field.name for field in cls.__dataclass_fields__.values()}
        missing = sorted(required_fields.difference(value))
        if missing:
            raise ValueError(f"Missing sensor fields: {', '.join(missing)}")
        return cls(**{name: value[name] for name in required_fields})
