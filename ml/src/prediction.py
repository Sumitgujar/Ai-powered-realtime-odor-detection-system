"""Load a trained artifact and predict odor, intensity, confidence, and anomaly."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

import joblib
import pandas as pd

from src.data_pipeline import SENSOR_COLUMNS
from src.preprocessing import engineer_features


class OdorPredictor:
    def __init__(self, model_path: str | Path) -> None:
        path = Path(model_path)
        if not path.is_file():
            raise FileNotFoundError(f"Trained model not found: {path}")
        self.artifact = joblib.load(path)
        required = {
            "odor_model",
            "intensity_model",
            "anomaly_model",
            "odor_classes",
            "intensity_classes",
        }
        missing = required.difference(self.artifact)
        if missing:
            raise ValueError(f"Invalid model artifact; missing: {', '.join(sorted(missing))}")

    def predict(self, sensor_reading: Mapping[str, Any]) -> dict[str, Any]:
        missing = [name for name in SENSOR_COLUMNS if name not in sensor_reading]
        if missing:
            raise ValueError(f"Missing sensor readings: {', '.join(missing)}")

        raw_frame = pd.DataFrame([{name: sensor_reading[name] for name in SENSOR_COLUMNS}])
        features = engineer_features(raw_frame)

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


def predict_sensor_reading(
    sensor_reading: Mapping[str, Any],
    model_path: str | Path | None = None,
) -> dict[str, Any]:
    default_path = Path(__file__).resolve().parents[1] / "models" / "odor_pipeline.joblib"
    return OdorPredictor(model_path or default_path).predict(sensor_reading)
