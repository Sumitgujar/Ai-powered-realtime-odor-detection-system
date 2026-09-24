"""Legacy and schema-v2 dataset loading for odor classification."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import pandas as pd

# Schema v1 is retained for historical datasets and the legacy model.
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

# Schema v2 matches the new NodeMCU sensor configuration. bme_gas is optional
# because not every BME68x-compatible board exposes the gas channel.
NEW_SCHEMA_VERSION = 2
NEW_DATASET_REQUIRED_COLUMNS = [
    "timestamp",
    "deviceId",
    "mq135",
    "temperature",
    "humidity",
    "pressure",
    "pir",
    "schemaVersion",
    "odor_label",
    "intensity_label",
]
NEW_DATASET_OPTIONAL_COLUMNS = ["bme_gas"]
NEW_LABEL_COLUMNS = ["odor_label", "intensity_label"]
NewDatasetKind = Literal["real_v2", "simulated_v2"]


def _validate_dataset_path(path: str | Path, dataset_kind: str) -> Path:
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
    return dataset_path


def load_dataset(path: str | Path, dataset_kind: DatasetKind) -> pd.DataFrame:
    """Load a legacy schema-v1 real or simulated CSV."""
    dataset_path = _validate_dataset_path(path, dataset_kind)
    frame = pd.read_csv(dataset_path)
    missing = [column for column in DATASET_COLUMNS if column not in frame.columns]
    unexpected = [column for column in frame.columns if column not in DATASET_COLUMNS]
    if missing or unexpected:
        details = []
        if missing:
            details.append(f"missing columns: {', '.join(missing)}")
        if unexpected:
            details.append(f"unexpected columns: {', '.join(unexpected)}")
        raise ValueError("Invalid legacy dataset schema (" + "; ".join(details) + ")")

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


def _coerce_pir_column(frame: pd.DataFrame) -> pd.Series:
    values = frame["pir"]
    if pd.api.types.is_bool_dtype(values):
        return values.astype(bool)
    if pd.api.types.is_numeric_dtype(values):
        numeric = pd.to_numeric(values, errors="coerce")
        if numeric.isna().any() or not numeric.isin([0, 1]).all():
            raise ValueError("pir must contain only boolean or 0/1 values")
        return numeric.astype(bool)
    normalized = values.astype(str).str.strip().str.lower()
    mapped = normalized.map({"true": True, "false": False, "1": True, "0": False})
    if mapped.isna().any():
        raise ValueError("pir must contain only true/false or 0/1 values")
    return mapped.astype(bool)


def load_new_dataset(path: str | Path, dataset_kind: NewDatasetKind) -> pd.DataFrame:
    """Load a labeled schema-v2 dataset without inventing removed fields."""
    dataset_path = _validate_dataset_path(path, dataset_kind)
    frame = pd.read_csv(dataset_path)
    missing = [
        column for column in NEW_DATASET_REQUIRED_COLUMNS if column not in frame.columns
    ]
    allowed = set(NEW_DATASET_REQUIRED_COLUMNS + NEW_DATASET_OPTIONAL_COLUMNS)
    unexpected = [column for column in frame.columns if column not in allowed]
    if missing or unexpected:
        details = []
        if missing:
            details.append(f"missing columns: {', '.join(missing)}")
        if unexpected:
            details.append(f"unexpected columns: {', '.join(unexpected)}")
        raise ValueError("Invalid schema-v2 dataset (" + "; ".join(details) + ")")

    columns = [column for column in NEW_DATASET_REQUIRED_COLUMNS if column in frame.columns]
    if "bme_gas" in frame.columns:
        columns.append("bme_gas")
    frame = frame[columns].copy()
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True, errors="coerce")
    frame["schemaVersion"] = pd.to_numeric(frame["schemaVersion"], errors="coerce")
    for column in ("mq135", "temperature", "humidity", "pressure", "bme_gas"):
        if column in frame.columns:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame["pir"] = _coerce_pir_column(frame)

    if frame["schemaVersion"].isna().any() or not frame["schemaVersion"].eq(NEW_SCHEMA_VERSION).all():
        raise ValueError(f"schemaVersion must be {NEW_SCHEMA_VERSION} for all rows")
    if frame["timestamp"].isna().any():
        raise ValueError("schema-v2 dataset contains invalid timestamps")
    if frame["deviceId"].isna().any() or not frame["deviceId"].astype(str).str.strip().all():
        raise ValueError("deviceId cannot be missing or blank")
    for label in NEW_LABEL_COLUMNS:
        if frame[label].isna().any() or not frame[label].astype(str).str.strip().all():
            raise ValueError(f"{label} cannot be missing or blank")
        frame[label] = frame[label].astype(str).str.strip()
    if len(frame) < 20:
        raise ValueError("Schema-v2 dataset must contain at least 20 rows")
    return frame
