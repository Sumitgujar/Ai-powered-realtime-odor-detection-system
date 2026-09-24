"""Train and persist a schema-v2 odor model without legacy sensor features."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib

from src.data_pipeline import NEW_SCHEMA_VERSION, load_new_dataset
from src.evaluate import evaluate_model
from src.new_preprocessing import engineer_new_features


def _build_candidates(random_state: int) -> dict[str, Any]:
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.pipeline import Pipeline

    candidates: dict[str, Any] = {
        "random_forest": Pipeline(
            steps=[
                ("preprocessor", _build_preprocessor()),
                (
                    "classifier",
                    RandomForestClassifier(
                        n_estimators=250,
                        class_weight="balanced",
                        random_state=random_state,
                        n_jobs=-1,
                    ),
                ),
            ]
        )
    }
    try:
        from xgboost import XGBClassifier
    except (ImportError, OSError):
        return candidates

    candidates["xgboost"] = Pipeline(
        steps=[
            ("preprocessor", _build_preprocessor()),
            (
                "classifier",
                XGBClassifier(
                    n_estimators=200,
                    max_depth=5,
                    learning_rate=0.08,
                    subsample=0.9,
                    colsample_bytree=0.9,
                    eval_metric="mlogloss",
                    random_state=random_state,
                    n_jobs=-1,
                ),
            ),
        ]
    )
    return candidates


def _build_preprocessor():
    from sklearn.impute import SimpleImputer
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler

    return Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("normalizer", StandardScaler()),
        ]
    )


def train_new_models(
    dataset_path: str | Path,
    dataset_kind: str,
    output_path: str | Path,
    random_state: int = 42,
    include_pir: bool = False,
) -> dict[str, object]:
    """Train only from labeled schema-v2 data supplied by the user."""
    from sklearn.ensemble import IsolationForest, RandomForestClassifier
    from sklearn.model_selection import train_test_split
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import LabelEncoder

    frame = load_new_dataset(dataset_path, dataset_kind)  # type: ignore[arg-type]
    features = engineer_new_features(frame, include_pir=include_pir)

    odor_encoder = LabelEncoder()
    intensity_encoder = LabelEncoder()
    odor_targets = odor_encoder.fit_transform(frame["odor_label"])
    intensity_targets = intensity_encoder.fit_transform(frame["intensity_label"])

    indices = list(range(len(frame)))
    train_indices, test_indices = train_test_split(
        indices,
        test_size=0.25,
        random_state=random_state,
        stratify=odor_targets,
    )
    x_train = features.iloc[train_indices]
    x_test = features.iloc[test_indices]
    y_odor_train = odor_targets[train_indices]
    y_odor_test = odor_targets[test_indices]
    y_intensity_train = intensity_targets[train_indices]

    model_metrics: list[dict[str, object]] = []
    fitted_candidates: dict[str, Any] = {}
    for name, model in _build_candidates(random_state).items():
        try:
            model.fit(x_train, y_odor_train)
            fitted_candidates[name] = model
            model_metrics.append(evaluate_model(name, model, x_test, y_odor_test))
        except Exception as exc:
            if name == "xgboost":
                model_metrics.append({"model": name, "status": f"unavailable: {exc}"})
                continue
            raise

    successful_metrics = [row for row in model_metrics if "f1" in row]
    if not successful_metrics:
        raise RuntimeError("No schema-v2 classifier trained successfully")
    best_name = str(max(successful_metrics, key=lambda row: float(row["f1"]))["model"])

    intensity_model = Pipeline(
        steps=[
            ("preprocessor", _build_preprocessor()),
            (
                "classifier",
                RandomForestClassifier(
                    n_estimators=200,
                    class_weight="balanced",
                    random_state=random_state,
                    n_jobs=-1,
                ),
            ),
        ]
    )
    intensity_model.fit(x_train, y_intensity_train)

    anomaly_model = Pipeline(
        steps=[
            ("preprocessor", _build_preprocessor()),
            (
                "detector",
                IsolationForest(
                    n_estimators=200,
                    contamination=0.05,
                    random_state=random_state,
                    n_jobs=-1,
                ),
            ),
        ]
    )
    anomaly_model.fit(x_train)

    source_is_simulated = dataset_kind == "simulated_v2"
    artifact = {
        "artifact_type": "odor_pipeline_v2",
        "schemaVersion": NEW_SCHEMA_VERSION,
        "odor_model": fitted_candidates[best_name],
        "intensity_model": intensity_model,
        "anomaly_model": anomaly_model,
        "odor_classes": odor_encoder.classes_.tolist(),
        "intensity_classes": intensity_encoder.classes_.tolist(),
        "feature_columns": features.columns.tolist(),
        "include_pir": include_pir,
        "bme_gas_included": "bme_gas" in features.columns,
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "dataset_kind": dataset_kind,
        "metrics": model_metrics,
        "best_model": best_name,
        "legacy_compatible": False,
        "evaluation_notice": (
            "Development metrics from schema-v2 simulated data; not real-world accuracy."
            if source_is_simulated
            else "Metrics apply only to the supplied labeled schema-v2 real-data split."
        ),
    }

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(artifact, output)
    return {
        "best_model": best_name,
        "metrics": model_metrics,
        "model_path": str(output.resolve()),
        "feature_columns": features.columns.tolist(),
        "include_pir": include_pir,
        "evaluation_notice": artifact["evaluation_notice"],
        "rows": len(frame),
    }


def parse_args() -> argparse.Namespace:
    ml_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dataset",
        default=str(ml_root / "data" / "simulated_v2" / "schema_v2_sensor_data.csv"),
    )
    parser.add_argument(
        "--dataset-kind", choices=("real_v2", "simulated_v2"), default="simulated_v2"
    )
    parser.add_argument(
        "--output", default=str(ml_root / "models" / "odor_pipeline_v2.joblib")
    )
    parser.add_argument("--random-state", type=int, default=42)
    parser.add_argument(
        "--include-pir",
        action="store_true",
        help="Explicitly include PIR context; use only after evaluation justifies it.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        result = train_new_models(
            args.dataset,
            args.dataset_kind,
            args.output,
            args.random_state,
            args.include_pir,
        )
    except Exception as exc:
        print(f"Schema-v2 training failed: {exc}")
        return 1
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
