"""Write one simulated reading to Firebase and verify its read-back."""

from __future__ import annotations

from app.core.config import Settings
from app.services.firebase_service import FirebaseSensorService
from simulator import generate_sensor_reading


def main() -> int:
    try:
        settings = Settings.from_env()
        service = FirebaseSensorService(settings)
        expected = generate_sensor_reading("simulator-verification", 18.5204, 73.8567)
        reading_id = service.write_sensor_reading(expected)
        actual = service.read_sensor_reading(reading_id)
        if actual != expected:
            print("FAILED: Firebase read-back did not match the written reading")
            return 1
        if not actual.is_simulated:
            print("FAILED: verification reading was not marked as simulated")
            return 1
        print(f"PASS: simulator -> Firebase -> read-back verified ({reading_id})")
        return 0
    except (ValueError, LookupError, RuntimeError) as exc:
        print(f"FAILED: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
