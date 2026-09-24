# Odor classification pipelines

This package now contains two explicitly separated pipelines:

- **Legacy schema v1** — retained for historical ESP32 records and any existing legacy artifact.
- **Schema v2** — for the NodeMCU + MQ135 + BME680/BME68x + PIR configuration.

Do not compare schema-v1 and schema-v2 metrics as if they were the same model.

## Schema v2 dataset

Place labeled schema-v2 datasets in one of these directories:

```text
ml/data/real_v2/
ml/data/simulated_v2/
```

Required columns:

```text
timestamp,deviceId,mq135,temperature,humidity,pressure,pir,schemaVersion,odor_label,intensity_label
```

Optional column:

```text
bme_gas
```

`bme_gas` is included only when the actual BME680/BME68x hardware provides a usable gas reading. Missing BME gas data is not replaced with a fabricated value.

The legacy sample dataset remains under `ml/data/simulated/` and is not valid schema-v2 training data.

## Schema-v2 feature policy

The new pipeline uses:

- `mq135`
- `temperature`
- `humidity`
- `pressure`
- optional `bme_gas`
- temperature/humidity index
- absolute humidity proxy
- environment-compensated MQ135
- optional environment-compensated BME gas

It does not use:

- MQ136
- MQ3
- GPS latitude/longitude
- removed-sensor ratios
- BME688-only gas-scanner features

PIR is retained as context/presence data and is excluded from odor-model features by default. The `--include-pir` option exists only for an explicit comparison after evaluation justifies it.

## Train the new model

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

After supplying a real labeled schema-v2 dataset:

```bash
python -m unittest discover -s tests -v
python -m src.train_new \
  --dataset ml/data/real_v2/your_labeled_data.csv \
  --dataset-kind real_v2 \
  --output ml/models/odor_pipeline_v2.joblib
```

For development-only simulated data, use `simulated_v2` only when a clearly labeled, user-approved simulated dataset exists. This repository does not fabricate one.

The artifact records `schemaVersion`, exact feature ordering, whether BME gas was included, whether PIR was included, metrics, dataset kind, and an evaluation notice. The new artifact is intentionally not compatible with the legacy predictor.

## Inference

Use `src.new_prediction.NewOdorPredictor` with `odor_pipeline_v2.joblib`. It rejects schema-v1 payloads and does not fill missing removed-sensor fields.

FastAPI routes schema-v2 payloads to `NewOdorPredictor` and historical schema-v1 payloads to the legacy `OdorPredictor`; it rejects requests when the matching artifact is unavailable.

## Retraining requirement

A legacy model's accuracy, confidence, intensity, or anomaly behavior does not transfer to the new sensor configuration. A new labeled dataset and new model artifact are required before schema-v2 production inference.
