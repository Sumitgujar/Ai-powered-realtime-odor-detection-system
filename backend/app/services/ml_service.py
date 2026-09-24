"""Version-aware adapters for legacy and schema-v2 ML artifacts."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Mapping


class MLServiceError(RuntimeError):
    pass


class MLPredictionService:
    def __init__(
        self,
        model_path: str | Path | None,
        legacy_model_path: str | Path | None = None,
    ) -> None:
        ml_root = Path(__file__).resolve().parents[3] / "ml"
        if str(ml_root) not in sys.path:
            sys.path.insert(0, str(ml_root))
        self.model_path = Path(model_path) if model_path else None
        self.legacy_model_path = Path(legacy_model_path) if legacy_model_path else None
        self._new_predictor = self._load_new_predictor(self.model_path)
        self._legacy_predictor = self._load_legacy_predictor(self.legacy_model_path)
        if self._new_predictor is None and self._legacy_predictor is None:
            raise MLServiceError(
                "No trained ML model found; configure ML_MODEL_PATH and/or LEGACY_ML_MODEL_PATH"
            )

    @staticmethod
    def _load_new_predictor(path: Path | None):
        if path is None or not path.is_file():
            return None
        try:
            from src.new_prediction import NewOdorPredictor

            return NewOdorPredictor(path)
        except Exception as exc:
            raise MLServiceError(f"Unable to load schema-v2 ML model: {exc}") from exc

    @staticmethod
    def _load_legacy_predictor(path: Path | None):
        if path is None or not path.is_file():
            return None
        try:
            from src.prediction import OdorPredictor

            return OdorPredictor(path)
        except Exception as exc:
            raise MLServiceError(f"Unable to load legacy ML model: {exc}") from exc

    def predict(
        self, sensor_reading: Mapping[str, Any], schema_version: int = 2
    ) -> dict[str, Any]:
        predictor = self._new_predictor if schema_version == 2 else self._legacy_predictor
        if predictor is None:
            model_name = "schema-v2" if schema_version == 2 else "legacy schema-v1"
            raise MLServiceError(f"{model_name} model is unavailable; retraining is required")
        try:
            prediction = predictor.predict(sensor_reading)
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
        return self._new_predictor is not None or self._legacy_predictor is not None
