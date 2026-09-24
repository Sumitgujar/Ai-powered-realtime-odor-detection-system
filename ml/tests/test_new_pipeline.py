"""Schema-v2 feature tests without fabricating a new labeled dataset."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

from src.data_pipeline import load_dataset
from src.new_preprocessing import engineer_new_features

ML_ROOT = Path(__file__).resolve().parents[1]
LEGACY_SAMPLE = ML_ROOT / "data" / "simulated" / "sample_simulated_sensor_data.csv"


class NewFeaturePipelineTests(unittest.TestCase):
    def test_new_features_exclude_removed_sensors_and_gps(self) -> None:
        legacy_frame = load_dataset(LEGACY_SAMPLE, "simulated")
        input_frame = legacy_frame[
            ["mq135", "temperature", "humidity", "pressure", "bme_gas"]
        ].copy()
        features = engineer_new_features(input_frame)
        self.assertIn("mq135", features.columns)
        self.assertIn("bme_gas", features.columns)
        self.assertIn("mq135_compensated", features.columns)
        self.assertIn("bme_gas_compensated", features.columns)
        for removed in ("mq136", "mq3", "latitude", "longitude", "pir_context"):
            self.assertNotIn(removed, features.columns)

    def test_pir_is_context_only_by_default(self) -> None:
        legacy_frame = load_dataset(LEGACY_SAMPLE, "simulated")
        input_frame = legacy_frame[["mq135", "temperature", "humidity", "pressure"]].copy()
        input_frame["pir"] = False
        default_features = engineer_new_features(input_frame)
        context_features = engineer_new_features(input_frame, include_pir=True)
        self.assertNotIn("pir_context", default_features.columns)
        self.assertIn("pir_context", context_features.columns)

    def test_v2_loader_does_not_accept_legacy_dataset_location(self) -> None:
        from src.data_pipeline import load_new_dataset

        with self.assertRaises(ValueError):
            load_new_dataset(LEGACY_SAMPLE, "simulated_v2")


@unittest.skipUnless(
    importlib.util.find_spec("joblib"), "joblib is not installed"
)
class NewInferenceTests(unittest.TestCase):
    def test_missing_new_model_is_not_silently_replaced(self) -> None:
        from src.new_prediction import NewOdorPredictor

        with self.assertRaises(FileNotFoundError):
            NewOdorPredictor(ML_ROOT / "models" / "odor_pipeline_v2.joblib")


if __name__ == "__main__":
    unittest.main()
