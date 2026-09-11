"""Dataset loading and schema validation for odor-classification data."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import pandas as pd

DATASET_COLUMNS = [
    "timestamp",
    "device_id",
    "mq135",
    "mq136",
    "mq3",
    "bme_gas",
    "temperature",
    "humidity",
    "pressure",
    "latitude",
    "longitude",
    "odor_label",
    "intensity_label",
]

SENSOR_COLUMNS = [
    "mq135",
    "mq136",
    "mq3",
    "bme_gas",
    "temperature",
    "humidity",
    "pressure",
    "latitude",
    "longitude",
]

LABEL_COLUMNS = ["odor_label", "intensity_label"]
DatasetKind = Literal["real", "simulated"]


def load_dataset(path: str | Path, dataset_kind: DatasetKind) -> pd.DataFrame:
    """Load a real or simulated CSV and enforce the canonical schema."""
    dataset_path = Path(path).resolve()
    expected_folder = Path(__file__).resolve().parents[1] / "data" / dataset_kind
    try:
        dataset_path.relative_to(expected_folder.resolve())
    except ValueError as exc:
        raise ValueError(
            f"{dataset_kind} datasets must be stored under {expected_folder}"
        ) from exc

    if not dataset_path.is_file():
        raise FileNotFoundError(f"Dataset not found: {dataset_path}")

    frame = pd.read_csv(dataset_path)
    missing = [column for column in DATASET_COLUMNS if column not in frame.columns]
    unexpected = [column for column in frame.columns if column not in DATASET_COLUMNS]
    if missing or unexpected:
        details = []
        if missing:
            details.append(f"missing columns: {', '.join(missing)}")
        if unexpected:
            details.append(f"unexpected columns: {', '.join(unexpected)}")
        raise ValueError("Invalid dataset schema (" + "; ".join(details) + ")")

    frame = frame[DATASET_COLUMNS].copy()
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True, errors="coerce")
    for column in SENSOR_COLUMNS:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")

    if frame["timestamp"].isna().all():
        raise ValueError("Dataset contains no valid timestamps")
    if frame["device_id"].isna().all() or not frame["device_id"].astype(str).str.strip().any():
        raise ValueError("Dataset contains no valid device_id values")
    for label in LABEL_COLUMNS:
        if frame[label].isna().any() or not frame[label].astype(str).str.strip().all():
            raise ValueError(f"{label} cannot be missing or blank")
        frame[label] = frame[label].astype(str).str.strip()
    if len(frame) < 20:
        raise ValueError("Dataset must contain at least 20 rows")
    return frame
