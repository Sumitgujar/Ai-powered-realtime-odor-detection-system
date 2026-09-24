"""HTTP routes for versioned sensor, Firebase, and ML operations."""

from __future__ import annotations

import logging
from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Query, Request, status

from app.models.api import (
    AlertRecord,
    DeviceRecord,
    HealthResponse,
    LegacyAlertRecord,
    LegacyPredictionResponse,
    LegacySensorDataRecord,
    LegacySensorReadingRequest,
    PredictionResponse,
    SensorDataRecord,
    SensorReadingRequest,
)
from app.models.sensor_data import SensorReading
from app.services.ml_service import MLServiceError

logger = logging.getLogger(__name__)
router = APIRouter()
Limit = Annotated[int, Query(ge=1, le=1000)]
SensorInput = SensorReadingRequest | LegacySensorReadingRequest
PredictionOutput = PredictionResponse | LegacyPredictionResponse
SensorOutput = SensorDataRecord | LegacySensorDataRecord
AlertOutput = AlertRecord | LegacyAlertRecord


def _firebase(request: Request):
    service = request.app.state.firebase_service
    if service is None:
        raise HTTPException(status_code=503, detail="Firebase service is unavailable")
    return service


def _ml(request: Request):
    service = request.app.state.ml_service
    if service is None:
        raise HTTPException(
            status_code=503,
            detail="ML model is unavailable; train and configure the matching schema model",
        )
    return service


def _firebase_result(operation):
    try:
        return operation()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        logger.exception("Firebase operation failed")
        raise HTTPException(status_code=503, detail=str(exc)) from exc


def _risk_level(odor_class: str, intensity: str, anomaly: bool, confidence: float) -> str:
    if anomaly:
        return "critical"
    if confidence < 0.5:
        return "review"
    if odor_class != "clean_air" and intensity.lower() == "high":
        return "high"
    if odor_class != "clean_air" or intensity.lower() == "medium":
        return "moderate"
    return "low"


def _timestamp(value) -> str:
    return value.isoformat().replace("+00:00", "Z")


@router.post(
    "/predict",
    response_model=PredictionOutput,
    response_model_exclude_none=True,
    summary="Store a versioned sensor reading and run matching ML inference",
)
def predict(payload: SensorInput, request: Request) -> dict[str, Any]:
    firebase = _firebase(request)
    ml_service = _ml(request)
    sensor_payload = payload.model_dump(mode="json", exclude_none=True)
    sensor_payload["timestamp"] = _timestamp(payload.timestamp)

    is_v2 = isinstance(payload, SensorReadingRequest)
    schema_version = 2 if is_v2 else 1
    device_id = payload.deviceId if is_v2 else payload.device_id

    try:
        if is_v2:
            reading_id = firebase.write_new_sensor_payload(sensor_payload)
        else:
            legacy_payload = dict(sensor_payload)
            legacy_payload.pop("schemaVersion", None)
            reading_id = firebase.write_sensor_reading(SensorReading(**legacy_payload))

        prediction = ml_service.predict(sensor_payload, schema_version=schema_version)
        risk = _risk_level(
            str(prediction["odor_class"]),
            str(prediction["intensity"]),
            bool(prediction["is_anomaly"]),
            float(prediction["confidence"]),
        )
        persisted_prediction: dict[str, Any] = {
            "timestamp": sensor_payload["timestamp"],
            "reading_id": reading_id,
            "odor_class": str(prediction["odor_class"]),
            "intensity": str(prediction["intensity"]),
            "anomaly_status": bool(prediction["is_anomaly"]),
            "confidence": float(prediction["confidence"]),
            "prediction_risk": risk,
        }
        if is_v2:
            persisted_prediction.update({"deviceId": device_id, "schemaVersion": 2})
        else:
            persisted_prediction["device_id"] = device_id

        prediction_id = firebase.write_prediction(device_id, persisted_prediction)
        if persisted_prediction["anomaly_status"] or risk in {"high", "critical"}:
            firebase.write_alert(device_id, persisted_prediction)
        logger.info(
            "Prediction completed device=%s reading_id=%s schema=%s risk=%s",
            device_id,
            reading_id,
            schema_version,
            risk,
        )
        return {**persisted_prediction, "prediction_id": prediction_id}
    except MLServiceError as exc:
        logger.exception("ML prediction failed for device=%s", device_id)
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except (ValueError, TypeError) as exc:
        logger.warning("Prediction input failed validation: %s", exc)
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except RuntimeError as exc:
        logger.exception("Prediction persistence failed for device=%s", device_id)
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get(
    "/sensor-data",
    response_model=list[SensorOutput],
    response_model_exclude_none=True,
    summary="List legacy and schema-v2 sensor readings",
)
def sensor_data(
    request: Request,
    device_id: str | None = None,
    limit: Limit = 100,
    schema_version: int | None = Query(default=None, ge=1, le=2),
):
    return _firebase_result(
        lambda: _firebase(request).list_sensor_data(
            device_id=device_id, limit=limit, schema_version=schema_version
        )
    )


@router.get("/devices", response_model=list[DeviceRecord], summary="List known devices")
def devices(request: Request):
    return _firebase_result(lambda: _firebase(request).list_devices())


@router.get(
    "/latest",
    response_model=list[SensorOutput],
    response_model_exclude_none=True,
    summary="Get latest readings",
)
def latest(request: Request, device_id: str | None = None):
    return _firebase_result(lambda: _firebase(request).latest(device_id=device_id))


@router.get(
    "/alerts",
    response_model=list[AlertOutput],
    response_model_exclude_none=True,
    summary="List prediction alerts",
)
def alerts(request: Request, device_id: str | None = None, limit: Limit = 100):
    return _firebase_result(
        lambda: _firebase(request).list_alerts(device_id=device_id, limit=limit)
    )


@router.get("/health", response_model=HealthResponse, summary="Check API dependencies")
def health(request: Request):
    firebase_ok = bool(
        request.app.state.firebase_service
        and request.app.state.firebase_service.healthcheck()
    )
    ml_ok = bool(request.app.state.ml_service and request.app.state.ml_service.healthcheck())
    return {
        "status": "healthy" if firebase_ok and ml_ok else "degraded",
        "api": "ok",
        "firebase": "ok" if firebase_ok else "unavailable",
        "ml_model": "ok" if ml_ok else "unavailable",
        "version": request.app.state.settings.app_version,
    }
