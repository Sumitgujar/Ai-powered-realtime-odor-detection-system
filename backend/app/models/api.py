"""Pydantic request and response models for schema-v1 and schema-v2 records."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class _TimestampedModel(BaseModel):
    @field_validator("timestamp", check_fields=False)
    @classmethod
    def validate_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamp must include a timezone")
        return value.astimezone(timezone.utc)


class _FirebaseDeviceIdModel(BaseModel):
    @staticmethod
    def validate_firebase_device_id(value: str) -> str:
        value = value.strip()
        if not value or any(character in value for character in ".#$[]/"):
            raise ValueError("device ID contains a character not allowed in Firebase keys")
        return value


class SensorReadingRequest(_TimestampedModel, _FirebaseDeviceIdModel):
    """Current schema-v2 request. Field names match the device contract."""

    model_config = ConfigDict(extra="forbid")

    deviceId: str = Field(min_length=1, max_length=64, examples=["nodemcu-1234abcd"])
    timestamp: datetime = Field(examples=["2026-09-24T18:00:00Z"])
    mq135: float = Field(ge=0, le=4095, examples=[740.0])
    temperature: float = Field(ge=-40, le=85, examples=[27.4])
    humidity: float = Field(ge=0, le=100, examples=[58.0])
    pressure: float = Field(ge=300, le=1100, examples=[1007.5])
    bme_gas: float | None = Field(default=None, ge=0, le=10_000_000)
    pir: bool
    schemaVersion: Literal[2]

    @field_validator("deviceId")
    @classmethod
    def validate_device_id(cls, value: str) -> str:
        return cls.validate_firebase_device_id(value)


class LegacySensorReadingRequest(_TimestampedModel, _FirebaseDeviceIdModel):
    """Read/predict compatibility for existing schema-v1 ESP32 records."""

    model_config = ConfigDict(extra="forbid")

    device_id: str = Field(min_length=1, max_length=64)
    timestamp: datetime
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    bme_gas: float = Field(ge=0, le=10_000_000)
    mq135: float = Field(ge=0, le=4095)
    mq136: float = Field(ge=0, le=4095)
    mq3: float = Field(ge=0, le=4095)
    temperature: float = Field(ge=-40, le=85)
    humidity: float = Field(ge=0, le=100)
    pressure: float = Field(ge=300, le=1100)
    is_simulated: bool = False
    schemaVersion: Literal[1] | None = None

    @field_validator("device_id")
    @classmethod
    def validate_device_id(cls, value: str) -> str:
        return cls.validate_firebase_device_id(value)


class PredictionResponse(BaseModel):
    odor_class: str
    intensity: str
    anomaly_status: bool
    confidence: float = Field(ge=0, le=1)
    prediction_risk: Literal["low", "moderate", "high", "critical", "review"]
    timestamp: datetime
    deviceId: str
    schemaVersion: Literal[2]
    reading_id: str
    prediction_id: str


class LegacyPredictionResponse(BaseModel):
    odor_class: str
    intensity: str
    anomaly_status: bool
    confidence: float = Field(ge=0, le=1)
    prediction_risk: Literal["low", "moderate", "high", "critical", "review"]
    timestamp: datetime
    device_id: str
    reading_id: str
    prediction_id: str


class SensorDataRecord(SensorReadingRequest):
    reading_id: str


class LegacySensorDataRecord(LegacySensorReadingRequest):
    reading_id: str


class DeviceRecord(BaseModel):
    device_id: str
    latest_timestamp: datetime | None = None


class AlertRecord(BaseModel):
    alert_id: str
    deviceId: str
    schemaVersion: Literal[2]
    timestamp: datetime
    odor_class: str
    intensity: str
    anomaly_status: bool
    confidence: float
    prediction_risk: str


class LegacyAlertRecord(BaseModel):
    alert_id: str
    device_id: str
    timestamp: datetime
    odor_class: str
    intensity: str
    anomaly_status: bool
    confidence: float
    prediction_risk: str


class HealthResponse(BaseModel):
    status: Literal["healthy", "degraded"]
    api: Literal["ok"] = "ok"
    firebase: Literal["ok", "unavailable"]
    ml_model: Literal["ok", "unavailable"]
    version: str


class ErrorResponse(BaseModel):
    detail: str
    error_code: str
