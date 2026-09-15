"""Firebase Realtime Database operations for sensor data, predictions, and alerts."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from app.core.config import Settings
from app.models.sensor_data import SensorReading

ReferenceFactory = Callable[[str], Any]


class FirebaseSensorService:
    def __init__(
        self,
        settings: Settings,
        reference_factory: ReferenceFactory | None = None,
    ) -> None:
        self.settings = settings
        self._reference_factory = reference_factory or self._create_reference_factory()
        self._root = self._reference_factory(settings.sensor_data_path)
        self._predictions_root = self._reference_factory(settings.predictions_path)
        self._alerts_root = self._reference_factory(settings.alerts_path)

    def _create_reference_factory(self) -> ReferenceFactory:
        if not self.settings.firebase_project_id or not self.settings.firebase_database_url:
            raise RuntimeError("Firebase environment configuration is incomplete")
        try:
            import firebase_admin
            from firebase_admin import credentials, db
        except ImportError as exc:
            raise RuntimeError(
                "firebase-admin is not installed; run pip install -r requirements.txt"
            ) from exc

        try:
            app = firebase_admin.get_app()
        except ValueError:
            try:
                if self.settings.firebase_credentials_path:
                    credential_path = Path(self.settings.firebase_credentials_path)
                    if not credential_path.is_file():
                        raise FileNotFoundError(
                            f"Firebase credential file not found: {credential_path}"
                        )
                    credential = credentials.Certificate(str(credential_path))
                else:
                    credential = credentials.ApplicationDefault()
                app = firebase_admin.initialize_app(
                    credential,
                    {
                        "databaseURL": self.settings.firebase_database_url,
                        "projectId": self.settings.firebase_project_id,
                    },
                )
            except Exception as exc:
                raise RuntimeError(f"Unable to initialize Firebase: {exc}") from exc

        return lambda path: db.reference(path, app=app)

    def write_sensor_reading(self, reading: SensorReading) -> str:
        validated = SensorReading.from_dict(reading.to_dict())
        try:
            created_ref = self._root.child(validated.device_id).push(validated.to_dict())
        except Exception as exc:
            raise RuntimeError(f"Failed to write sensor reading: {exc}") from exc
        if not getattr(created_ref, "key", None):
            raise RuntimeError("Firebase did not return a key for the sensor reading")
        return f"{validated.device_id}/{created_ref.key}"

    def read_sensor_reading(self, reading_id: str) -> SensorReading:
        device_id, key = self._split_record_id(reading_id)
        try:
            payload = self._root.child(device_id).child(key).get()
        except Exception as exc:
            raise RuntimeError(f"Failed to read sensor reading: {exc}") from exc
        if payload is None:
            raise LookupError(f"Sensor reading not found: {reading_id}")
        return SensorReading.from_dict(payload)

    def read_latest(self, device_id: str, limit: int = 10) -> list[SensorReading]:
        records = self.list_sensor_data(device_id=device_id, limit=limit)
        return [SensorReading.from_dict(self._without_ids(record)) for record in records]

    def list_sensor_data(
        self, device_id: str | None = None, limit: int = 100
    ) -> list[dict[str, Any]]:
        self._validate_limit(limit)
        try:
            if device_id:
                payload = (
                    self._root.child(device_id)
                    .order_by_child("timestamp")
                    .limit_to_last(limit)
                    .get()
                ) or {}
                records = self._flatten_device_records(device_id, payload)
            else:
                payload = self._root.get() or {}
                records = []
                if not isinstance(payload, dict):
                    raise ValueError("Firebase returned an unexpected sensor-data shape")
                for current_device, device_records in payload.items():
                    records.extend(
                        self._flatten_device_records(current_device, device_records or {})
                    )
            return sorted(records, key=lambda item: item.get("timestamp", ""), reverse=True)[:limit]
        except (ValueError, TypeError):
            raise
        except Exception as exc:
            raise RuntimeError(f"Failed to list sensor readings: {exc}") from exc

    def list_devices(self) -> list[dict[str, Any]]:
        try:
            payload = self._root.get() or {}
        except Exception as exc:
            raise RuntimeError(f"Failed to list devices: {exc}") from exc
        if not isinstance(payload, dict):
            raise ValueError("Firebase returned an unexpected device-data shape")
        devices = []
        for device_id, records in payload.items():
            flattened = self._flatten_device_records(device_id, records or {})
            latest_timestamp = max(
                (record.get("timestamp") for record in flattened), default=None
            )
            devices.append({"device_id": device_id, "latest_timestamp": latest_timestamp})
        return sorted(devices, key=lambda item: item["device_id"])

    def latest(self, device_id: str | None = None) -> list[dict[str, Any]]:
        if device_id:
            return self.list_sensor_data(device_id=device_id, limit=1)
        latest_records = []
        for device in self.list_devices():
            records = self.list_sensor_data(device_id=device["device_id"], limit=1)
            latest_records.extend(records)
        return sorted(
            latest_records, key=lambda item: item.get("timestamp", ""), reverse=True
        )

    def write_prediction(self, device_id: str, prediction: dict[str, Any]) -> str:
        try:
            created_ref = self._predictions_root.child(device_id).push(prediction)
        except Exception as exc:
            raise RuntimeError(f"Failed to write prediction: {exc}") from exc
        if not getattr(created_ref, "key", None):
            raise RuntimeError("Firebase did not return a prediction key")
        return f"{device_id}/{created_ref.key}"

    def write_alert(self, device_id: str, alert: dict[str, Any]) -> str:
        try:
            created_ref = self._alerts_root.child(device_id).push(alert)
        except Exception as exc:
            raise RuntimeError(f"Failed to write alert: {exc}") from exc
        if not getattr(created_ref, "key", None):
            raise RuntimeError("Firebase did not return an alert key")
        return f"{device_id}/{created_ref.key}"

    def list_alerts(
        self, device_id: str | None = None, limit: int = 100
    ) -> list[dict[str, Any]]:
        self._validate_limit(limit)
        try:
            payload = self._alerts_root.get() or {}
        except Exception as exc:
            raise RuntimeError(f"Failed to list alerts: {exc}") from exc
        if not isinstance(payload, dict):
            raise ValueError("Firebase returned an unexpected alert-data shape")
        records = []
        for current_device, device_alerts in payload.items():
            if device_id and current_device != device_id:
                continue
            if not isinstance(device_alerts, dict):
                continue
            for key, value in device_alerts.items():
                if isinstance(value, dict):
                    records.append({"alert_id": f"{current_device}/{key}", **value})
        return sorted(records, key=lambda item: item.get("timestamp", ""), reverse=True)[:limit]

    def healthcheck(self) -> bool:
        try:
            self._root.get()
            return True
        except Exception:
            return False

    @staticmethod
    def _validate_limit(limit: int) -> None:
        if not 1 <= limit <= 1000:
            raise ValueError("limit must be between 1 and 1000")

    @staticmethod
    def _split_record_id(record_id: str) -> tuple[str, str]:
        parts = record_id.strip("/").split("/")
        if len(parts) != 2 or not all(parts):
            raise ValueError("record ID must use '<device_id>/<firebase_key>' format")
        return parts[0], parts[1]

    @staticmethod
    def _flatten_device_records(device_id: str, payload: Any) -> list[dict[str, Any]]:
        if not isinstance(payload, dict):
            raise ValueError("Firebase returned an unexpected sensor-data shape")
        return [
            {"reading_id": f"{device_id}/{key}", **value}
            for key, value in payload.items()
            if isinstance(value, dict)
        ]

    @staticmethod
    def _without_ids(record: dict[str, Any]) -> dict[str, Any]:
        return {key: value for key, value in record.items() if key != "reading_id"}
