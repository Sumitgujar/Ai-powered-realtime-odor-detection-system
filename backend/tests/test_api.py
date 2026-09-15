"""Endpoint tests with isolated Firebase and ML adapters."""

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


SAMPLE = {
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
        self.readings = []
        self.predictions = []
        self.alerts = []

    def write_sensor_reading(self, reading):
        record = reading.to_dict()
        record["reading_id"] = f"{reading.device_id}/reading-1"
        self.readings.append(record)
        return record["reading_id"]

    def write_prediction(self, device_id, prediction):
        self.predictions.append(deepcopy(prediction))
        return f"{device_id}/prediction-1"

    def write_alert(self, device_id, alert):
        record = {"alert_id": f"{device_id}/alert-1", **deepcopy(alert)}
        self.alerts.append(record)
        return record["alert_id"]

    def list_sensor_data(self, device_id=None, limit=100):
        values = [
            item for item in self.readings if not device_id or item["device_id"] == device_id
        ]
        return list(reversed(values))[:limit]

    def list_devices(self):
        return [
            {"device_id": "esp32-test-001", "latest_timestamp": SAMPLE["timestamp"]}
        ] if self.readings else []

    def latest(self, device_id=None):
        values = self.list_sensor_data(device_id=device_id, limit=1)
        return values

    def list_alerts(self, device_id=None, limit=100):
        values = [
            item for item in self.alerts if not device_id or item["device_id"] == device_id
        ]
        return values[:limit]

    def healthcheck(self):
        return True


class FakeMLService:
    def predict(self, _sensor_reading):
        return {
            "odor_class": "smoke",
            "intensity": "high",
            "confidence": 0.91,
            "is_anomaly": True,
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
            create_app(
                settings=settings,
                firebase_service=self.firebase,
                ml_service=FakeMLService(),
            )
        )

    def test_health(self):
        response = self.client.get("/health")
        self.assertEqual(200, response.status_code)
        self.assertEqual("healthy", response.json()["status"])

    def test_predict(self):
        response = self.client.post("/predict", json=SAMPLE)
        self.assertEqual(200, response.status_code)
        body = response.json()
        self.assertEqual("smoke", body["odor_class"])
        self.assertEqual("high", body["intensity"])
        self.assertTrue(body["anomaly_status"])
        self.assertEqual("critical", body["prediction_risk"])
        self.assertEqual("esp32-test-001", body["device_id"])

    def test_predict_validation_error(self):
        invalid = {**SAMPLE, "humidity": 101}
        response = self.client.post("/predict", json=invalid)
        self.assertEqual(422, response.status_code)

    def test_sensor_data(self):
        self.client.post("/predict", json=SAMPLE)
        response = self.client.get("/sensor-data?device_id=esp32-test-001&limit=10")
        self.assertEqual(200, response.status_code)
        self.assertEqual(1, len(response.json()))

    def test_devices(self):
        self.client.post("/predict", json=SAMPLE)
        response = self.client.get("/devices")
        self.assertEqual(200, response.status_code)
        self.assertEqual("esp32-test-001", response.json()[0]["device_id"])

    def test_latest(self):
        self.client.post("/predict", json=SAMPLE)
        response = self.client.get("/latest?device_id=esp32-test-001")
        self.assertEqual(200, response.status_code)
        self.assertEqual(1, len(response.json()))

    def test_alerts(self):
        self.client.post("/predict", json=SAMPLE)
        response = self.client.get("/alerts?device_id=esp32-test-001")
        self.assertEqual(200, response.status_code)
        self.assertEqual("critical", response.json()[0]["prediction_risk"])

    def test_openapi_documentation(self):
        response = self.client.get("/openapi.json")
        self.assertEqual(200, response.status_code)
        for path in ("/predict", "/sensor-data", "/devices", "/latest", "/alerts", "/health"):
            self.assertIn(path, response.json()["paths"])


if __name__ == "__main__":
    unittest.main()
