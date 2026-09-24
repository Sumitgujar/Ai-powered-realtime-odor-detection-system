"""Tests schema/model routing without requiring trained artifacts."""

import unittest

from app.services.ml_service import MLPredictionService, MLServiceError


class Predictor:
    def __init__(self, label):
        self.label = label

    def predict(self, _payload):
        return {
            "odor_class": self.label,
            "intensity": "low",
            "confidence": 0.9,
            "is_anomaly": False,
        }


class MlServiceRoutingTests(unittest.TestCase):
    def service(self):
        service = object.__new__(MLPredictionService)
        service._new_predictor = Predictor("v2")
        service._legacy_predictor = Predictor("v1")
        return service

    def test_routes_to_matching_predictor(self):
        service = self.service()
        self.assertEqual("v2", service.predict({}, schema_version=2)["odor_class"])
        self.assertEqual("v1", service.predict({}, schema_version=1)["odor_class"])

    def test_rejects_missing_matching_model(self):
        service = self.service()
        service._new_predictor = None
        with self.assertRaises(MLServiceError):
            service.predict({}, schema_version=2)


if __name__ == "__main__":
    unittest.main()
