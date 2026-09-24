"""Pydantic validation tests that do not require FastAPI."""

from __future__ import annotations

import unittest

from pydantic import ValidationError

from app.models.api import LegacySensorReadingRequest, SensorReadingRequest


class ApiModelTests(unittest.TestCase):
    def test_schema_v2_accepts_optional_bme_gas_absent(self):
        model = SensorReadingRequest.model_validate({
            "deviceId": "nodemcu-1",
            "timestamp": "2026-09-24T18:00:00Z",
            "mq135": 500,
            "temperature": 25,
            "humidity": 50,
            "pressure": 1000,
            "pir": False,
            "schemaVersion": 2,
        })
        self.assertIsNone(model.bme_gas)

    def test_schema_v2_rejects_removed_fields(self):
        with self.assertRaises(ValidationError):
            SensorReadingRequest.model_validate({
                "deviceId": "nodemcu-1",
                "timestamp": "2026-09-24T18:00:00Z",
                "mq135": 500,
                "mq136": 100,
                "temperature": 25,
                "humidity": 50,
                "pressure": 1000,
                "pir": False,
                "schemaVersion": 2,
            })

    def test_legacy_model_remains_available(self):
        model = LegacySensorReadingRequest.model_validate({
            "device_id": "esp32-1",
            "timestamp": "2026-09-12T05:30:00Z",
            "latitude": 1,
            "longitude": 2,
            "bme_gas": 1000,
            "mq135": 100,
            "mq136": 200,
            "mq3": 300,
            "temperature": 25,
            "humidity": 50,
            "pressure": 1000,
            "is_simulated": False,
        })
        self.assertEqual("esp32-1", model.device_id)


if __name__ == "__main__":
    unittest.main()
