"""Forecast accuracy metrics. All take numpy-like arrays of equal length."""
from __future__ import annotations

import numpy as np


def mape(y_true, y_pred) -> float:
    """Mean Absolute Percentage Error, guarded against zeros in y_true."""
    y_true, y_pred = np.asarray(y_true, dtype=float), np.asarray(y_pred, dtype=float)
    mask = np.abs(y_true) > 1e-6
    if not mask.any():
        return 0.0
    return float(np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100.0)


def wape(y_true, y_pred) -> float:
    """Weighted Absolute Percentage Error — sum of absolute errors / sum of actuals."""
    y_true, y_pred = np.asarray(y_true, dtype=float), np.asarray(y_pred, dtype=float)
    denom = np.sum(np.abs(y_true))
    if denom < 1e-8:
        return 0.0
    return float(np.sum(np.abs(y_true - y_pred)) / denom * 100.0)


def smape(y_true, y_pred) -> float:
    """Symmetric MAPE — bounded 0-200%, robust to near-zero actuals."""
    y_true, y_pred = np.asarray(y_true, dtype=float), np.asarray(y_pred, dtype=float)
    denom = np.abs(y_true) + np.abs(y_pred)
    mask = denom > 1e-6
    if not mask.any():
        return 0.0
    return float(np.mean(2 * np.abs(y_pred[mask] - y_true[mask]) / denom[mask]) * 100.0)


def mase(y_true, y_pred, y_train_history) -> float:
    """Mean Absolute Scaled Error — MAE scaled by the naive (lag-1) in-sample error."""
    y_true, y_pred = np.asarray(y_true, dtype=float), np.asarray(y_pred, dtype=float)
    hist = np.asarray(y_train_history, dtype=float)
    if len(hist) < 2:
        return 0.0
    naive_errors = np.abs(np.diff(hist))
    scale = np.mean(naive_errors)
    if scale < 1e-8:
        return 0.0
    return float(np.mean(np.abs(y_true - y_pred)) / scale)


def bias(y_true, y_pred) -> float:
    """Mean error — positive means the model over-forecasts on average."""
    y_true, y_pred = np.asarray(y_true, dtype=float), np.asarray(y_pred, dtype=float)
    return float(np.mean(y_pred - y_true))


def all_metrics(y_true, y_pred, y_train_history) -> dict:
    return {
        "mape": round(mape(y_true, y_pred), 2),
        "wape": round(wape(y_true, y_pred), 2),
        "smape": round(smape(y_true, y_pred), 2),
        "mase": round(mase(y_true, y_pred, y_train_history), 3),
        "bias": round(bias(y_true, y_pred), 2),
    }
