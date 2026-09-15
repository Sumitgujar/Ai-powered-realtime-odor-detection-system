"""HTTP routes for sensor, Firebase, and ML bridge operations."""

from __future__ import annotations

import logging
from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Query, Request, status

from app.models.api import (
    AlertRecord,
    DeviceRecord,
    HealthResponse,
    PredictionResponse,
    SensorDataRecord,
    SensorReadingRequest,
)
from app.models.sensor_data import SensorReading
from app.services.ml_service import MLServiceError

logger = logging.getLogger(__name__)
router = APIRouter()
Limit = Annotated[int, Query(ge=1, le=1000)]


def _firebase(request: Request):
    service = request.app.state.firebase_service
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Firebase service is unavailable",
        )
    return service


def _ml(request: Request):
    service = request.app.state.ml_service
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ML model is unavailable; train the model and configure ML_MODEL_PATH",
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


@router.post(
    "/predict",
    response_model=PredictionResponse,
    summary="Store a sensor reading and run odor prediction",
    responses={503: {"description": "Firebase or ML model unavailable"}},
)
def predict(payload: SensorReadingRequest, request: Request) -> dict[str, Any]:
    firebase = _firebase(request)
    ml_service = _ml(request)
    timestamp = payload.timestamp.isoformat().replace("+00:00", "Z")
    sensor_payload = payload.model_dump()
    sensor_payload["timestamp"] = timestamp

    try:
        reading = SensorReading(**sensor_payload)
        reading_id = firebase.write_sensor_reading(reading)
        prediction = ml_service.predict(sensor_payload)
        risk = _risk_level(
            str(prediction["odor_class"]),
            str(prediction["intensity"]),
            bool(prediction["is_anomaly"]),
            float(prediction["confidence"]),
        )
        persisted_prediction = {
            "device_id": payload.device_id,
            "timestamp": timestamp,
            "reading_id": reading_id,
            "odor_class": str(prediction["odor_class"]),
            "intensity": str(prediction["intensity"]),
            "anomaly_status": bool(prediction["is_anomaly"]),
            "confidence": float(prediction["confidence"]),
            "prediction_risk": risk,
        }
        prediction_id = firebase.write_prediction(payload.device_id, persisted_prediction)
        if persisted_prediction["anomaly_status"] or risk in {"high", "critical"}:
            firebase.write_alert(payload.device_id, persisted_prediction)
        logger.info(
            "Prediction completed device_id=%s reading_id=%s risk=%s",
            payload.device_id,
            reading_id,
            risk,
        )
        return {**persisted_prediction, "prediction_id": prediction_id}
    except HTTPException:
        raise
    except MLServiceError as exc:
        logger.exception("ML prediction failed for device_id=%s", payload.device_id)
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except (ValueError, TypeError) as exc:
        logger.warning("Prediction input failed validation: %s", exc)
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except RuntimeError as exc:
        logger.exception("Prediction persistence failed for device_id=%s", payload.device_id)
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/sensor-data", response_model=list[SensorDataRecord], summary="List sensor readings")
def sensor_data(
    request: Request,
    device_id: str | None = None,
    limit: Limit = 100,
):
    return _firebase_result(
        lambda: _firebase(request).list_sensor_data(device_id=device_id, limit=limit)
    )


@router.get("/devices", response_model=list[DeviceRecord], summary="List known devices")
def devices(request: Request):
    return _firebase_result(lambda: _firebase(request).list_devices())


@router.get("/latest", response_model=list[SensorDataRecord], summary="Get latest readings")
def latest(request: Request, device_id: str | None = None):
    return _firebase_result(lambda: _firebase(request).latest(device_id=device_id))


@router.get("/alerts", response_model=list[AlertRecord], summary="List prediction alerts")
def alerts(
    request: Request,
    device_id: str | None = None,
    limit: Limit = 100,
):
    return _firebase_result(
        lambda: _firebase(request).list_alerts(device_id=device_id, limit=limit)
    )


@router.get("/health", response_model=HealthResponse, summary="Check API dependencies")
def health(request: Request):
    firebase_ok = bool(
        request.app.state.firebase_service
        and request.app.state.firebase_service.healthcheck()
    )
    ml_ok = bool(
        request.app.state.ml_service and request.app.state.ml_service.healthcheck()
    )
    return {
        "status": "healthy" if firebase_ok and ml_ok else "degraded",
        "api": "ok",
        "firebase": "ok" if firebase_ok else "unavailable",
        "ml_model": "ok" if ml_ok else "unavailable",
        "version": request.app.state.settings.app_version,
    }
