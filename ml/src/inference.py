"""Backward-compatible imports for the prediction interface."""

from src.prediction import OdorPredictor, predict_sensor_reading

__all__ = ["OdorPredictor", "predict_sensor_reading"]
