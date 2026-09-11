"""Local tests for validation and simulator-to-service read-back."""

from __future__ import annotations

import unittest
from copy import deepcopy

from app.core.config import Settings
from app.models.sensor_data import SensorReading
from app.services.firebase_service import FirebaseSensorService
from simulator import generate_sensor_reading


class FakeReference:
    def __init__(self, store: dict, path: tuple[str, ...] = ()) -> None:
        self.store = store
        self.path = path
        self.key: str | None = None
        self._limit: int | None = None

    def child(self, key: str) -> "FakeReference":
        return FakeReference(self.store, self.path + (key,))

    def push(self, value: dict) -> "FakeReference":
        container = self._resolve(create=True)
        key = f"test-key-{len(container) + 1}"
        container[key] = deepcopy(value)
        result = FakeReference(self.store, self.path + (key,))
        result.key = key
        return result

    def get(self):
        value = self._resolve(create=False)
        if isinstance(value, dict) and self._limit is not None:
            values = sorted(value.items(), key=lambda item: item[1]["timestamp"])
            return dict(values[-self._limit :])
        return deepcopy(value)

    def order_by_child(self, _name: str) -> "FakeReference":
        return self

    def limit_to_last(self, limit: int) -> "FakeReference":
        self._limit = limit
        return self

    def _resolve(self, create: bool):
        current = self.store
        for part in self.path:
            if create:
                current = current.setdefault(part, {})
            elif not isinstance(current, dict) or part not in current:
                return None
            else:
                current = current[part]
        return current


class IngestionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.store: dict = {}
        settings = Settings(
            firebase_project_id="test-project",
            firebase_database_url="https://test-project.firebaseio.com",
            firebase_credentials_path=None,
        )
        self.service = FirebaseSensorService(
            settings,
            reference_factory=lambda path: FakeReference(self.store, (path,)),
        )

    def test_simulator_to_database_read_back(self) -> None:
        generated = generate_sensor_reading(
            "simulator-test", 18.5204, 73.8567
        )
        reading_id = self.service.write_sensor_reading(generated)
        read_back = self.service.read_sensor_reading(reading_id)
        self.assertEqual(generated, read_back)
        self.assertTrue(read_back.is_simulated)

    def test_latest_readings(self) -> None:
        for _ in range(3):
            self.service.write_sensor_reading(
                generate_sensor_reading("simulator-test", 18.5204, 73.8567)
            )
        self.assertEqual(2, len(self.service.read_latest("simulator-test", limit=2)))

    def test_validation_rejects_invalid_humidity(self) -> None:
        reading = generate_sensor_reading("simulator-test", 18.5204, 73.8567)
        payload = reading.to_dict()
        payload["humidity"] = 101
        with self.assertRaises(ValueError):
            SensorReading.from_dict(payload)

    def test_schema_requires_simulation_marker(self) -> None:
        reading = generate_sensor_reading("simulator-test", 18.5204, 73.8567)
        payload = reading.to_dict()
        del payload["is_simulated"]
        with self.assertRaises(ValueError):
            SensorReading.from_dict(payload)


if __name__ == "__main__":
    unittest.main()
