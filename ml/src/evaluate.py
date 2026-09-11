"""Model evaluation helpers."""

from __future__ import annotations

from typing import Any


def classification_metrics(y_true, y_pred) -> dict[str, float]:
    """Calculate weighted multiclass metrics with stable zero-division behavior."""
    try:
        from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
    except ImportError as exc:
        raise RuntimeError("scikit-learn is required for evaluation") from exc

    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision": float(precision_score(y_true, y_pred, average="weighted", zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, average="weighted", zero_division=0)),
        "f1": float(f1_score(y_true, y_pred, average="weighted", zero_division=0)),
    }


def evaluate_model(name: str, model: Any, x_test, y_test) -> dict[str, object]:
    predictions = model.predict(x_test)
    return {"model": name, **classification_metrics(y_test, predictions)}
