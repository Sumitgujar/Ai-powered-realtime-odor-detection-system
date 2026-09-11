"""Generate a deterministic simulated dataset for development and tests only."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from src.data_pipeline import DATASET_COLUMNS


def generate_sample_dataset(row_count: int = 360, seed: int = 42) -> pd.DataFrame:
    if row_count < 60:
        raise ValueError("row_count must be at least 60")
    rng = np.random.default_rng(seed)
    odor_profiles = {
        "clean_air": (260, 190, 130, 32000),
        "smoke": (1450, 900, 420, 12500),
        "alcohol": (760, 380, 1800, 17500),
        "sulfur": (980, 1750, 330, 10500),
    }
    intensities = {"low": 0.75, "medium": 1.0, "high": 1.3}
    labels = list(odor_profiles)
    levels = list(intensities)
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    rows = []

    for index in range(row_count):
        odor_label = labels[index % len(labels)]
        intensity_label = levels[(index // len(labels)) % len(levels)]
        mq135, mq136, mq3, bme_gas = odor_profiles[odor_label]
        scale = intensities[intensity_label]
        temperature = rng.normal(26.0, 3.5)
        humidity = np.clip(rng.normal(55.0, 10.0), 25.0, 85.0)
        environmental_factor = 1 + 0.015 * (temperature - 25) + 0.006 * (humidity - 50)

        row = {
            "timestamp": (start + timedelta(seconds=30 * index)).isoformat().replace("+00:00", "Z"),
            "device_id": f"simulator-{1 + index % 3:03d}",
            "mq135": max(0, rng.normal(mq135 * scale * environmental_factor, mq135 * 0.08)),
            "mq136": max(0, rng.normal(mq136 * scale * environmental_factor, mq136 * 0.08)),
            "mq3": max(0, rng.normal(mq3 * scale * environmental_factor, mq3 * 0.08)),
            "bme_gas": max(0, rng.normal(bme_gas / scale * environmental_factor, bme_gas * 0.06)),
            "temperature": temperature,
            "humidity": humidity,
            "pressure": rng.normal(1008.0, 8.0),
            "latitude": 18.5204 + rng.normal(0, 0.0002),
            "longitude": 73.8567 + rng.normal(0, 0.0002),
            "odor_label": odor_label,
            "intensity_label": intensity_label,
        }
        rows.append(row)

    frame = pd.DataFrame(rows, columns=DATASET_COLUMNS)
    missing_rows = rng.choice(row_count, size=max(3, row_count // 40), replace=False)
    for row_index, column in zip(missing_rows, ["humidity", "mq136", "pressure"] * row_count):
        frame.loc[row_index, column] = np.nan
    return frame


def main() -> None:
    destination = Path(__file__).resolve().parent / "data" / "simulated" / "sample_simulated_sensor_data.csv"
    destination.parent.mkdir(parents=True, exist_ok=True)
    generate_sample_dataset().to_csv(destination, index=False)
    print(f"Created simulated development dataset: {destination}")


if __name__ == "__main__":
    main()
