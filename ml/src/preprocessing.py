"""Feature engineering, missing-value handling, and sensor normalization."""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.data_pipeline import SENSOR_COLUMNS

RAW_FEATURE_COLUMNS = SENSOR_COLUMNS.copy()
GAS_COLUMNS = ["mq135", "mq136", "mq3", "bme_gas"]
ENGINEERED_FEATURE_COLUMNS = [
    "temperature_humidity_index",
    "absolute_humidity_proxy",
    "mq135_compensated",
    "mq136_compensated",
    "mq3_compensated",
    "bme_gas_compensated",
    "mq135_mq136_ratio",
    "mq3_mq135_ratio",
]
MODEL_FEATURE_COLUMNS = RAW_FEATURE_COLUMNS + ENGINEERED_FEATURE_COLUMNS


def engineer_features(frame: pd.DataFrame) -> pd.DataFrame:
    """Create deterministic environment-compensated features from raw readings."""
    missing = [column for column in RAW_FEATURE_COLUMNS if column not in frame.columns]
    if missing:
        raise ValueError(f"Missing feature columns: {', '.join(missing)}")

    features = frame[RAW_FEATURE_COLUMNS].copy()
    for column in RAW_FEATURE_COLUMNS:
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
    for gas_column in GAS_COLUMNS:
        features[f"{gas_column}_compensated"] = features[gas_column] / compensation

    epsilon = 1e-6
    features["mq135_mq136_ratio"] = features["mq135"] / (
        features["mq136"].abs() + epsilon
    )
    features["mq3_mq135_ratio"] = features["mq3"] / (
        features["mq135"].abs() + epsilon
    )
    return features[MODEL_FEATURE_COLUMNS].replace([np.inf, -np.inf], np.nan)


def build_preprocessor():
    """Return a reusable median-imputation and standardization pipeline."""
    try:
        from sklearn.impute import SimpleImputer
        from sklearn.pipeline import Pipeline
        from sklearn.preprocessing import StandardScaler
    except ImportError as exc:
        raise RuntimeError(
            "scikit-learn is required; install dependencies from ml/requirements.txt"
        ) from exc

    return Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("normalizer", StandardScaler()),
        ]
    )
