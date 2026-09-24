"""Inference adapter for a schema-v2 model artifact."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

import joblib
import pandas as pd

from src.data_pipeline import NEW_SCHEMA_VERSION
from src.new_preprocessing import engineer_new_features


class NewModelError(RuntimeError):
    pass


class NewOdorPredictor:
    """Load only a model trained for the new sensor schema."""

    def __init__(self, model_path: str | Path) -> None:
        self.model_path = Path(model_path)
        if not self.model_path.is_file():
            raise FileNotFoundError(f"Schema-v2 model not found: {self.model_path}")
        self.artifact = joblib.load(self.model_path)
        required = {
            "artifact_type",
            "schemaVersion",
            "odor_model",
            "intensity_model",
            "anomaly_model",
            "odor_classes",
            "intensity_classes",
            "feature_columns",
            "include_pir",
        }
        missing = required.difference(self.artifact)
        if missing:
            raise NewModelError(
                "Invalid schema-v2 artifact; missing: " + ", ".join(sorted(missing))
            )
        if self.artifact["artifact_type"] != "odor_pipeline_v2":
            raise NewModelError("Model artifact is not a schema-v2 odor pipeline")
        if self.artifact["schemaVersion"] != NEW_SCHEMA_VERSION:
            raise NewModelError("Model artifact schemaVersion is not 2")

    def predict(self, sensor_reading: Mapping[str, Any]) -> dict[str, Any]:
        if sensor_reading.get("schemaVersion") != NEW_SCHEMA_VERSION:
            raise ValueError("schemaVersion must be 2 for schema-v2 inference")
        required = {
            "deviceId",
            "timestamp",
            "mq135",
            "temperature",
            "humidity",
            "pressure",
            "pir",
        }
        missing = sorted(required.difference(sensor_reading))
        if missing:
            raise ValueError("Missing schema-v2 sensor readings: " + ", ".join(missing))

        raw_frame = pd.DataFrame([dict(sensor_reading)])
        features = engineer_new_features(
            raw_frame,
            feature_columns=self.artifact["feature_columns"],
            include_pir=bool(self.artifact["include_pir"]),
        )
        odor_index = int(self.artifact["odor_model"].predict(features)[0])
        intensity_index = int(self.artifact["intensity_model"].predict(features)[0])
        probabilities = self.artifact["odor_model"].predict_proba(features)[0]
        anomaly_value = int(self.artifact["anomaly_model"].predict(features)[0])
        return {
            "odor_class": self.artifact["odor_classes"][odor_index],
            "intensity": self.artifact["intensity_classes"][intensity_index],
            "confidence": round(float(max(probabilities)), 6),
            "is_anomaly": anomaly_value == -1,
        }


def predict_new_sensor_reading(
    sensor_reading: Mapping[str, Any],
    model_path: str | Path,
) -> dict[str, Any]:
    return NewOdorPredictor(model_path).predict(sensor_reading)
