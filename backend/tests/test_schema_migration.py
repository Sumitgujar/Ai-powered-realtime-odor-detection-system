"""Tests for Firebase schema-v1 preservation and schema-v2 writes."""

from __future__ import annotations

import unittest
from copy import deepcopy

from app.core.config import Settings
from app.services.firebase_service import FirebaseSensorService
from app.services.sensor_schema import validate_new_sensor_payload
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


NEW_PAYLOAD = {
    "deviceId": "nodemcu-1234abcd",
    "timestamp": "2026-09-18T17:45:00Z",
    "mq135": 740.0,
    "temperature": 27.4,
    "humidity": 58.0,
    "pressure": 1007.5,
    "pir": True,
    "schemaVersion": 2,
}


class SchemaMigrationTests(unittest.TestCase):
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

    def test_new_payload_does_not_fabricate_optional_bme_gas(self) -> None:
        validated = validate_new_sensor_payload(NEW_PAYLOAD)
        self.assertNotIn("bme_gas", validated)
        self.assertNotIn("mq136", validated)
        self.assertNotIn("mq3", validated)
        self.assertNotIn("latitude", validated)
        self.assertNotIn("longitude", validated)

    def test_new_record_round_trip_and_schema_filter(self) -> None:
        reading_id = self.service.write_new_sensor_payload(NEW_PAYLOAD)
        self.assertEqual(NEW_PAYLOAD, self.service.read_new_sensor_payload(reading_id))
        raw = self.service.read_sensor_record(reading_id)
        self.assertEqual(NEW_PAYLOAD, raw)
        listed = self.service.list_sensor_data(schema_version=2)
        self.assertEqual(1, len(listed))
        self.assertEqual(raw, {key: value for key, value in listed[0].items() if key != "reading_id"})

    def test_legacy_record_is_preserved_and_classified_separately(self) -> None:
        legacy = generate_sensor_reading("simulator-test", 18.5204, 73.8567)
        legacy_id = self.service.write_sensor_reading(legacy)
        new_id = self.service.write_new_sensor_payload(NEW_PAYLOAD)
        self.assertEqual(legacy, self.service.read_sensor_reading(legacy_id))
        self.assertEqual(1, len(self.service.list_sensor_data(schema_version=1)))
        self.assertEqual(1, len(self.service.list_sensor_data(schema_version=2)))
        self.assertNotEqual(legacy_id, new_id)

    def test_invalid_schema_version_is_rejected(self) -> None:
        invalid = {**NEW_PAYLOAD, "schemaVersion": 1}
        with self.assertRaises(ValueError):
            self.service.write_new_sensor_payload(invalid)


if __name__ == "__main__":
    unittest.main()
