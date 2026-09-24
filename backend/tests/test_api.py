"""Endpoint tests for schema-v2 plus legacy compatibility."""

from __future__ import annotations

import importlib.util
import unittest
from copy import deepcopy

FASTAPI_TEST_AVAILABLE = bool(
    importlib.util.find_spec("fastapi") and importlib.util.find_spec("httpx")
)

if FASTAPI_TEST_AVAILABLE:
    from fastapi.testclient import TestClient
    from app.core.config import Settings
    from app.main import create_app

NEW_SAMPLE = {
    "deviceId": "nodemcu-test-001",
    "timestamp": "2026-09-24T18:00:00Z",
    "mq135": 740.0,
    "temperature": 27.4,
    "humidity": 58.0,
    "pressure": 1007.5,
    "pir": True,
    "schemaVersion": 2,
}
LEGACY_SAMPLE = {
    "device_id": "esp32-test-001",
    "timestamp": "2026-09-12T05:30:00Z",
    "latitude": 18.5204,
    "longitude": 73.8567,
    "bme_gas": 23000.0,
    "mq135": 740.0,
    "mq136": 410.0,
    "mq3": 250.0,
    "temperature": 27.4,
    "humidity": 58.0,
    "pressure": 1007.5,
    "is_simulated": True,
}


class FakeFirebaseService:
    def __init__(self) -> None:
        self.readings: list[dict] = []
        self.predictions: list[dict] = []
        self.alerts: list[dict] = []

    def write_new_sensor_payload(self, payload):
        record = deepcopy(payload)
        record["reading_id"] = f"{payload['deviceId']}/reading-v2"
        self.readings.append(record)
        return record["reading_id"]

    def write_sensor_reading(self, reading):
        record = reading.to_dict()
        record["reading_id"] = f"{reading.device_id}/reading-v1"
        self.readings.append(record)
        return record["reading_id"]

    def write_prediction(self, device_id, prediction):
        self.predictions.append(deepcopy(prediction))
        return f"{device_id}/prediction-1"

    def write_alert(self, device_id, alert):
        record = {"alert_id": f"{device_id}/alert-1", **deepcopy(alert)}
        self.alerts.append(record)
        return record["alert_id"]

    def list_sensor_data(self, device_id=None, limit=100, schema_version=None):
        values = self.readings
        if device_id:
            values = [r for r in values if r.get("deviceId", r.get("device_id")) == device_id]
        if schema_version:
            values = [r for r in values if r.get("schemaVersion", 1) == schema_version]
        return list(reversed(values))[:limit]

    def list_devices(self):
        ids = sorted({r.get("deviceId", r.get("device_id")) for r in self.readings})
        return [{"device_id": value, "latest_timestamp": NEW_SAMPLE["timestamp"]} for value in ids]

    def latest(self, device_id=None):
        return self.list_sensor_data(device_id=device_id, limit=1)

    def list_alerts(self, device_id=None, limit=100):
        values = [
            item for item in self.alerts
            if not device_id or item.get("deviceId", item.get("device_id")) == device_id
        ]
        return values[:limit]

    def healthcheck(self):
        return True


class FakeMLService:
    def predict(self, _sensor_reading, schema_version=2):
        return {
            "odor_class": "smoke" if schema_version == 2 else "clean_air",
            "intensity": "high" if schema_version == 2 else "low",
            "confidence": 0.91,
            "is_anomaly": schema_version == 2,
        }

    def healthcheck(self):
        return True


@unittest.skipUnless(FASTAPI_TEST_AVAILABLE, "fastapi and httpx are not installed")
class ApiEndpointTests(unittest.TestCase):
    def setUp(self):
        self.firebase = FakeFirebaseService()
        settings = Settings(
            firebase_project_id="test-project",
            firebase_database_url="https://test-project.firebaseio.com",
            firebase_credentials_path=None,
        )
        self.client = TestClient(
            create_app(settings, self.firebase, FakeMLService())
        )

    def test_health(self):
        response = self.client.get("/health")
        self.assertEqual(200, response.status_code)
        self.assertEqual("healthy", response.json()["status"])

    def test_predict_schema_v2_without_optional_bme_gas(self):
        response = self.client.post("/predict", json=NEW_SAMPLE)
        self.assertEqual(200, response.status_code)
        body = response.json()
        self.assertEqual("nodemcu-test-001", body["deviceId"])
        self.assertEqual(2, body["schemaVersion"])
        self.assertEqual("smoke", body["odor_class"])
        self.assertNotIn("bme_gas", self.firebase.readings[0])
        self.assertNotIn("mq136", self.firebase.readings[0])
        self.assertNotIn("latitude", self.firebase.readings[0])

    def test_predict_legacy_record(self):
        response = self.client.post("/predict", json=LEGACY_SAMPLE)
        self.assertEqual(200, response.status_code)
        self.assertEqual("esp32-test-001", response.json()["device_id"])

    def test_schema_v2_validation(self):
        invalid = {**NEW_SAMPLE, "schemaVersion": 1}
        self.assertEqual(422, self.client.post("/predict", json=invalid).status_code)
        invalid = {**NEW_SAMPLE, "humidity": 101}
        self.assertEqual(422, self.client.post("/predict", json=invalid).status_code)

    def test_sensor_endpoints_return_v2(self):
        self.client.post("/predict", json=NEW_SAMPLE)
        for path in (
            "/sensor-data?schema_version=2",
            "/latest?device_id=nodemcu-test-001",
            "/devices",
            "/alerts?device_id=nodemcu-test-001",
        ):
            self.assertEqual(200, self.client.get(path).status_code, path)

    def test_openapi_paths_preserved(self):
        response = self.client.get("/openapi.json")
        self.assertEqual(200, response.status_code)
        for path in ("/predict", "/sensor-data", "/devices", "/latest", "/alerts", "/health"):
            self.assertIn(path, response.json()["paths"])


if __name__ == "__main__":
    unittest.main()
