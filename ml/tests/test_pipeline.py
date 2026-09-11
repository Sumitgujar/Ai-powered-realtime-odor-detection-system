"""Tests for dataset validation, feature engineering, and end-to-end ML flow."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.data_pipeline import DATASET_COLUMNS, load_dataset
from src.preprocessing import ENGINEERED_FEATURE_COLUMNS, engineer_features

ML_ROOT = Path(__file__).resolve().parents[1]
SAMPLE_DATA = ML_ROOT / "data" / "simulated" / "sample_simulated_sensor_data.csv"


class DataPipelineTests(unittest.TestCase):
    def test_sample_dataset_schema_and_location(self) -> None:
        frame = load_dataset(SAMPLE_DATA, "simulated")
        self.assertEqual(DATASET_COLUMNS, frame.columns.tolist())
        self.assertGreaterEqual(len(frame), 20)

    def test_feature_engineering_preserves_rows(self) -> None:
        frame = load_dataset(SAMPLE_DATA, "simulated")
        features = engineer_features(frame)
        self.assertEqual(len(frame), len(features))
        for column in ENGINEERED_FEATURE_COLUMNS:
            self.assertIn(column, features.columns)


@unittest.skipUnless(
    __import__("importlib").util.find_spec("sklearn")
    and __import__("importlib").util.find_spec("joblib"),
    "scikit-learn and joblib are not installed",
)
class EndToEndPipelineTests(unittest.TestCase):
    def test_train_save_load_predict(self) -> None:
        from src.prediction import OdorPredictor
        from src.train import train_models

        with tempfile.TemporaryDirectory() as temporary_directory:
            model_path = Path(temporary_directory) / "odor_pipeline.joblib"
            result = train_models(SAMPLE_DATA, "simulated", model_path, random_state=7)
            self.assertTrue(model_path.is_file())
            self.assertIn(result["best_model"], {"random_forest", "xgboost"})

            frame = load_dataset(SAMPLE_DATA, "simulated")
            sample = frame.iloc[0].to_dict()
            prediction = OdorPredictor(model_path).predict(sample)
            self.assertEqual(
                {"odor_class", "intensity", "confidence", "is_anomaly"},
                set(prediction),
            )
            self.assertGreaterEqual(prediction["confidence"], 0.0)
            self.assertLessEqual(prediction["confidence"], 1.0)


if __name__ == "__main__":
    unittest.main()
