"""Versioned Firebase sensor payload validation and classification."""

from __future__ import annotations

import math
from datetime import datetime
from typing import Any, Mapping

LEGACY_SCHEMA_VERSION = 1
NEW_SCHEMA_VERSION = 2

NEW_REQUIRED_FIELDS = (
    "deviceId",
    "timestamp",
    "mq135",
    "temperature",
    "humidity",
    "pressure",
    "pir",
    "schemaVersion",
)
NEW_OPTIONAL_FIELDS = ("bme_gas",)


def _finite_number(name: str, value: Any, minimum: float, maximum: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a finite number")
    numeric = float(value)
    if not math.isfinite(numeric) or not minimum <= numeric <= maximum:
        raise ValueError(f"{name} must be between {minimum} and {maximum}")
    return numeric


def _validate_device_id(value: Any) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > 64:
        raise ValueError("deviceId must contain 1-64 characters")
    if any(char in value for char in ".#$[]/"):
        raise ValueError("deviceId contains a character not allowed in Firebase keys")
    return value


def _validate_timestamp(value: Any) -> str:
    if not isinstance(value, str):
        raise ValueError("timestamp must be an ISO-8601 string")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("timestamp must be a valid ISO-8601 value") from exc
    if parsed.tzinfo is None:
        raise ValueError("timestamp must include a timezone")
    return value


def validate_new_sensor_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Validate and return only the non-fabricated schema-v2 fields."""
    if not isinstance(payload, Mapping):
        raise ValueError("new sensor payload must be a mapping")

    missing = [field for field in NEW_REQUIRED_FIELDS if field not in payload]
    if missing:
        raise ValueError(f"Missing new sensor fields: {', '.join(missing)}")
    if payload["schemaVersion"] != NEW_SCHEMA_VERSION:
        raise ValueError(f"schemaVersion must be {NEW_SCHEMA_VERSION}")
    if not isinstance(payload["pir"], bool):
        raise ValueError("pir must be a boolean")

    validated: dict[str, Any] = {
        "deviceId": _validate_device_id(payload["deviceId"]),
        "timestamp": _validate_timestamp(payload["timestamp"]),
        "mq135": _finite_number("mq135", payload["mq135"], 0.0, 4095.0),
        "temperature": _finite_number("temperature", payload["temperature"], -40.0, 85.0),
        "humidity": _finite_number("humidity", payload["humidity"], 0.0, 100.0),
        "pressure": _finite_number("pressure", payload["pressure"], 300.0, 1100.0),
        "pir": payload["pir"],
        "schemaVersion": NEW_SCHEMA_VERSION,
    }
    if "bme_gas" in payload and payload["bme_gas"] is not None:
        validated["bme_gas"] = _finite_number(
            "bme_gas", payload["bme_gas"], 0.0, 10_000_000.0
        )
    return validated


def schema_version_for(payload: Mapping[str, Any]) -> int:
    """Classify without rewriting records or inventing missing fields."""
    if payload.get("schemaVersion") == NEW_SCHEMA_VERSION:
        return NEW_SCHEMA_VERSION
    return LEGACY_SCHEMA_VERSION


def is_new_sensor_payload(payload: Mapping[str, Any]) -> bool:
    return schema_version_for(payload) == NEW_SCHEMA_VERSION
