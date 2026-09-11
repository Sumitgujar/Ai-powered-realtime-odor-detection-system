"""Firebase Realtime Database read/write operations for sensor data."""

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

    def _create_reference_factory(self) -> ReferenceFactory:
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
        """Validate and push one reading; return `<device_id>/<firebase_key>`."""
        validated = SensorReading.from_dict(reading.to_dict())
        try:
            created_ref = self._root.child(validated.device_id).push(validated.to_dict())
        except Exception as exc:
            raise RuntimeError(f"Failed to write sensor reading: {exc}") from exc
        if not getattr(created_ref, "key", None):
            raise RuntimeError("Firebase did not return a key for the sensor reading")
        return f"{validated.device_id}/{created_ref.key}"

    def read_sensor_reading(self, reading_id: str) -> SensorReading:
        """Read and validate one reading using `<device_id>/<firebase_key>`."""
        parts = reading_id.strip("/").split("/")
        if len(parts) != 2 or not all(parts):
            raise ValueError("reading_id must use '<device_id>/<firebase_key>' format")
        try:
            payload = self._root.child(parts[0]).child(parts[1]).get()
        except Exception as exc:
            raise RuntimeError(f"Failed to read sensor reading: {exc}") from exc
        if payload is None:
            raise LookupError(f"Sensor reading not found: {reading_id}")
        try:
            return SensorReading.from_dict(payload)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Stored sensor reading is invalid: {exc}") from exc

    def read_latest(self, device_id: str, limit: int = 10) -> list[SensorReading]:
        if not 1 <= limit <= 1000:
            raise ValueError("limit must be between 1 and 1000")
        try:
            payload = (
                self._root.child(device_id)
                .order_by_child("timestamp")
                .limit_to_last(limit)
                .get()
            ) or {}
        except Exception as exc:
            raise RuntimeError(f"Failed to read latest sensor readings: {exc}") from exc
        if not isinstance(payload, dict):
            raise ValueError("Firebase returned an unexpected sensor-data shape")
        return [SensorReading.from_dict(item) for item in payload.values()]
