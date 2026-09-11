# Odor classification pipeline

This package is independent of the React application. It validates the canonical sensor dataset, engineers environmental compensation features, imputes missing sensor values, normalizes features, compares classifiers, trains intensity and anomaly models, and persists one artifact with `joblib`.

## Dataset schema

`timestamp, device_id, mq135, mq136, mq3, bme_gas, temperature, humidity, pressure, latitude, longitude, odor_label, intensity_label`

- Put measured datasets only in `data/real/`.
- Put generated datasets only in `data/simulated/`.
- `sample_simulated_sensor_data.csv` is synthetic and intended only for development and testing.

## Run

```bash
python -m pip install -r requirements.txt
python generate_sample_data.py
python -m unittest discover -s tests -v
python -m src.train
```

Use `src.prediction.OdorPredictor` or `predict_sensor_reading` to obtain `odor_class`, `intensity`, `confidence`, and `is_anomaly` from one sensor-reading mapping.

> Metrics produced from the included simulated dataset are development checks only and must never be presented as real-world accuracy.
