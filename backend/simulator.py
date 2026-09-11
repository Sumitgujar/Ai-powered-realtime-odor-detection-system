"""Generate and publish realistic simulated sensor readings."""

from __future__ import annotations

import argparse
import random
import time
from datetime import datetime, timezone

from app.core.config import Settings
from app.models.sensor_data import SensorReading
from app.services.firebase_service import FirebaseSensorService


def generate_sensor_reading(
    device_id: str,
    latitude: float,
    longitude: float,
    rng: random.Random | None = None,
) -> SensorReading:
    rng = rng or random.Random()
    return SensorReading(
        device_id=device_id,
        timestamp=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        latitude=round(latitude + rng.uniform(-0.00015, 0.00015), 6),
        longitude=round(longitude + rng.uniform(-0.00015, 0.00015), 6),
        bme_gas=round(rng.uniform(8_000, 45_000), 2),
        mq135=round(rng.uniform(250, 1_400), 2),
        mq136=round(rng.uniform(120, 900), 2),
        mq3=round(rng.uniform(80, 700), 2),
        temperature=round(rng.uniform(20, 34), 2),
        humidity=round(rng.uniform(35, 75), 2),
        pressure=round(rng.uniform(980, 1035), 2),
        is_simulated=True,
    )


def publish_simulated_readings(
    service: FirebaseSensorService,
    count: int,
    interval_seconds: float,
    device_id: str,
    latitude: float,
    longitude: float,
    seed: int | None = None,
) -> list[str]:
    if count < 1:
        raise ValueError("count must be at least 1")
    if interval_seconds < 0:
        raise ValueError("interval must not be negative")

    rng = random.Random(seed)
    reading_ids: list[str] = []
    for index in range(count):
        reading = generate_sensor_reading(device_id, latitude, longitude, rng)
        reading_id = service.write_sensor_reading(reading)
        reading_ids.append(reading_id)
        print(f"Wrote simulated reading {reading_id} at {reading.timestamp}")
        if index < count - 1:
            time.sleep(interval_seconds)
    return reading_ids


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, default=10)
    parser.add_argument("--interval", type=float, default=2.0)
    parser.add_argument("--device-id", default="simulator-001")
    parser.add_argument("--latitude", type=float, default=18.5204)
    parser.add_argument("--longitude", type=float, default=73.8567)
    parser.add_argument("--seed", type=int)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        settings = Settings.from_env()
        service = FirebaseSensorService(settings)
        publish_simulated_readings(
            service,
            args.count,
            args.interval,
            args.device_id,
            args.latitude,
            args.longitude,
            args.seed,
        )
    except (ValueError, RuntimeError) as exc:
        print(f"Simulator failed: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
