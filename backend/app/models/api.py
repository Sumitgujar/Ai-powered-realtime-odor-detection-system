"""Pydantic request and response models for the FastAPI bridge."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SensorReadingRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    device_id: str = Field(min_length=1, max_length=64, examples=["esp32-001"])
    timestamp: datetime = Field(examples=["2026-09-12T05:30:00Z"])
    latitude: float = Field(ge=-90, le=90, examples=[18.5204])
    longitude: float = Field(ge=-180, le=180, examples=[73.8567])
    bme_gas: float = Field(ge=0, le=10_000_000, examples=[23000.0])
    mq135: float = Field(ge=0, le=4095, examples=[740.0])
    mq136: float = Field(ge=0, le=4095, examples=[410.0])
    mq3: float = Field(ge=0, le=4095, examples=[250.0])
    temperature: float = Field(ge=-40, le=85, examples=[27.4])
    humidity: float = Field(ge=0, le=100, examples=[58.0])
    pressure: float = Field(ge=300, le=1100, examples=[1007.5])
    is_simulated: bool = Field(default=False)

    @field_validator("device_id")
    @classmethod
    def validate_device_id(cls, value: str) -> str:
        value = value.strip()
        if any(character in value for character in ".#$[]/"):
            raise ValueError("device_id contains a character not allowed in Firebase keys")
        return value

    @field_validator("timestamp")
    @classmethod
    def validate_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamp must include a timezone")
        return value.astimezone(timezone.utc)


class PredictionResponse(BaseModel):
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


class DeviceRecord(BaseModel):
    device_id: str
    latest_timestamp: datetime | None = None


class AlertRecord(BaseModel):
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
