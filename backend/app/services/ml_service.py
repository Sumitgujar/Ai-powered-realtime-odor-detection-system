"""Adapter that loads the independent ML package for API predictions."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Mapping


class MLServiceError(RuntimeError):
    pass


class MLPredictionService:
    def __init__(self, model_path: str | Path) -> None:
        self.model_path = Path(model_path)
        self._predictor = self._load_predictor()

    def _load_predictor(self):
        if not self.model_path.is_file():
            raise MLServiceError(f"Trained ML model not found: {self.model_path}")
        ml_root = Path(__file__).resolve().parents[3] / "ml"
        if str(ml_root) not in sys.path:
            sys.path.insert(0, str(ml_root))
        try:
            from src.prediction import OdorPredictor

            return OdorPredictor(self.model_path)
        except Exception as exc:
            raise MLServiceError(f"Unable to load trained ML model: {exc}") from exc

    def predict(self, sensor_reading: Mapping[str, Any]) -> dict[str, Any]:
        try:
            prediction = self._predictor.predict(sensor_reading)
        except (TypeError, ValueError) as exc:
            raise MLServiceError(f"ML preprocessing or prediction failed: {exc}") from exc
        except Exception as exc:
            raise MLServiceError(f"ML prediction failed: {exc}") from exc
        required = {"odor_class", "intensity", "confidence", "is_anomaly"}
        missing = required.difference(prediction)
        if missing:
            raise MLServiceError(
                f"ML prediction is missing fields: {', '.join(sorted(missing))}"
            )
        return prediction

    def healthcheck(self) -> bool:
        return self.model_path.is_file() and self._predictor is not None
