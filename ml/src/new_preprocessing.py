"""Feature engineering for the schema-v2 NodeMCU sensor configuration."""

from __future__ import annotations

from typing import Sequence

import numpy as np
import pandas as pd

NEW_BASE_SENSOR_COLUMNS = ["mq135", "temperature", "humidity", "pressure"]
NEW_OPTIONAL_SENSOR_COLUMNS = ["bme_gas"]
NEW_ENGINEERED_FEATURE_COLUMNS = [
    "temperature_humidity_index",
    "absolute_humidity_proxy",
    "mq135_compensated",
]
NEW_BME_ENGINEERED_FEATURE = "bme_gas_compensated"
NEW_PIR_FEATURE = "pir_context"


def _available_sensor_columns(frame: pd.DataFrame) -> list[str]:
    missing = [column for column in NEW_BASE_SENSOR_COLUMNS if column not in frame.columns]
    if missing:
        raise ValueError(f"Missing schema-v2 feature columns: {', '.join(missing)}")
    columns = NEW_BASE_SENSOR_COLUMNS.copy()
    if "bme_gas" in frame.columns and frame["bme_gas"].notna().any():
        columns.append("bme_gas")
    return columns


def _pir_values(values: pd.Series) -> pd.Series:
    if pd.api.types.is_bool_dtype(values):
        return values.astype(float)
    if pd.api.types.is_numeric_dtype(values):
        numeric = pd.to_numeric(values, errors="coerce")
        if numeric.isna().any() or not numeric.isin([0, 1]).all():
            raise ValueError("pir must contain only boolean or 0/1 values")
        return numeric.astype(float)
    normalized = values.astype(str).str.strip().str.lower()
    mapped = normalized.map({"true": 1.0, "false": 0.0, "1": 1.0, "0": 0.0})
    if mapped.isna().any():
        raise ValueError("pir must contain only true/false or 0/1 values")
    return mapped.astype(float)


def engineer_new_features(
    frame: pd.DataFrame,
    feature_columns: Sequence[str] | None = None,
    include_pir: bool = False,
) -> pd.DataFrame:
    """Create only features supported by the new sensors.

    PIR is excluded by default because it is presence/context information, not
    an odor measurement. A trained artifact must explicitly opt into it.
    """
    raw_columns = _available_sensor_columns(frame)
    features = frame[raw_columns].copy()
    for column in raw_columns:
        features[column] = pd.to_numeric(features[column], errors="coerce")

    temperature = features["temperature"]
    humidity = features["humidity"]
    features["temperature_humidity_index"] = temperature * (humidity / 100.0)
    features["absolute_humidity_proxy"] = (
        (humidity / 100.0)
        * 6.112
        * np.exp((17.67 * temperature) / (temperature + 243.5))
    )

    compensation = 1.0 + 0.015 * (temperature - 25.0) + 0.006 * (humidity - 50.0)
    compensation = compensation.clip(lower=0.25, upper=4.0)
    features["mq135_compensated"] = features["mq135"] / compensation
    if "bme_gas" in raw_columns:
        features[NEW_BME_ENGINEERED_FEATURE] = features["bme_gas"] / compensation

    if include_pir:
        if "pir" not in frame.columns:
            raise ValueError("PIR was requested but the payload has no pir field")
        features[NEW_PIR_FEATURE] = _pir_values(frame["pir"])

    generated_columns = raw_columns + NEW_ENGINEERED_FEATURE_COLUMNS
    if "bme_gas" in raw_columns:
        generated_columns.append(NEW_BME_ENGINEERED_FEATURE)
    if include_pir:
        generated_columns.append(NEW_PIR_FEATURE)

    selected_columns = list(feature_columns) if feature_columns is not None else generated_columns
    missing = [column for column in selected_columns if column not in generated_columns]
    if missing:
        raise ValueError(
            "Requested feature columns are unavailable for this payload: "
            + ", ".join(missing)
        )
    return features[selected_columns].replace([np.inf, -np.inf], np.nan)
