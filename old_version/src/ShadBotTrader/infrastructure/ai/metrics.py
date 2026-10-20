"""Metric calculators (regression, classification, trading)."""

from __future__ import annotations

import math
from typing import Sequence


def regression_metrics(actual: Sequence[float], predicted: Sequence[float]) -> dict[str, float]:
    """MAE, RMSE and MAPE for paired actual/predicted series."""
    pairs = list(zip(actual, predicted, strict=False))
    if not pairs:
        return {"mae": 0.0, "rmse": 0.0, "mape": 0.0, "n": 0}
    mae = sum(abs(a - p) for a, p in pairs) / len(pairs)
    mse = sum((a - p) ** 2 for a, p in pairs) / len(pairs)
    rmse = math.sqrt(mse)
    mape = 0.0
    valid = 0
    for a, p in pairs:
        if a != 0:
            mape += abs((a - p) / a)
            valid += 1
    mape = (mape / valid * 100.0) if valid else 0.0
    return {"mae": mae, "rmse": rmse, "mape": mape, "n": len(pairs)}


def classification_metrics(
    actual: Sequence[int], predicted: Sequence[int], num_classes: int
) -> dict[str, float]:
    """Accuracy and per-class precision/recall/f1 (macro averaged)."""
    pairs = list(zip(actual, predicted, strict=False))
    if not pairs:
        return {"accuracy": 0.0, "precision": 0.0, "recall": 0.0, "f1": 0.0, "n": 0}

    correct = sum(1 for a, p in pairs if a == p)
    accuracy = correct / len(pairs)

    precisions: list[float] = []
    recalls: list[float] = []
    for cls in range(num_classes):
        tp = sum(1 for a, p in pairs if a == cls and p == cls)
        fp = sum(1 for a, p in pairs if a != cls and p == cls)
        fn = sum(1 for a, p in pairs if a == cls and p != cls)
        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        precisions.append(precision)
        recalls.append(recall)

    precision = sum(precisions) / num_classes
    recall = sum(recalls) / num_classes
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return {
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "n": len(pairs),
    }


def trading_metrics(
    predicted_direction: Sequence[int], realized: Sequence[float]
) -> dict[str, float]:
    """Hit rate and profit factor of directional predictions.

    ``predicted_direction``: +1 / -1 (long/short), 0 ignored.
    ``realized``: the outcome each prediction corresponds to (positive
    when the predicted direction was correct).
    """
    wins = 0
    losses = 0
    gross_win = 0.0
    gross_loss = 0.0
    for direction, outcome in zip(predicted_direction, realized, strict=False):
        if direction == 0:
            continue
        if outcome >= 0:
            wins += 1
            gross_win += outcome
        else:
            losses += 1
            gross_loss += abs(outcome)
    total = wins + losses
    hit_rate = wins / total if total else 0.0
    profit_factor = (gross_win / gross_loss) if gross_loss else float("inf")
    return {
        "hit_rate": hit_rate,
        "profit_factor": profit_factor,
        "trades": total,
    }
