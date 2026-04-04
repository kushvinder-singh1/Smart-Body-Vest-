"""
Inference-only helpers: load saved scaler (never fit), validate feature order, probability smoothing.

Training code must not import this module for scaling fit — use data_prep only for fit().
"""
from __future__ import annotations

import os
import pickle
from collections import deque
from typing import Any, Deque, List, Optional, Tuple

import numpy as np

from . import config

# Canonical training column order — must match data_prep FEATURE_COLS_SEQ row layout
FEATURE_ORDER_TRAINING: Tuple[str, ...] = tuple(config.FEATURE_COLS_SEQ)


def assert_feature_order_matches_config() -> None:
    expected = [
        "body_temperature_C",
        "temp_delta",
        "pulse_bpm",
        "motion_level_0_1",
        "age_years",
        "height_cm",
        "weight_kg",
        "gender_0_1",
        "temp_step",
        "pulse_step",
    ]
    got = list(config.FEATURE_COLS_SEQ)
    if got != expected:
        raise AssertionError(
            "FEATURE_COLS_SEQ must match training order [temp, temp_delta, ...]: %s vs %s"
            % (got, expected)
        )


def validate_runtime_feature_vector(vec: np.ndarray) -> None:
    """Single timestep: length must be FEATURE_DIM_SEQ; order is FEATURE_ORDER_TRAINING."""
    v = np.asarray(vec, dtype=np.float64).reshape(-1)
    if v.size != config.FEATURE_DIM_SEQ:
        raise ValueError(
            "Feature vector length must be %s (training order %s); got %s"
            % (config.FEATURE_DIM_SEQ, list(FEATURE_ORDER_TRAINING), v.size)
        )


def validate_raw_feature_matrix(raw: np.ndarray) -> None:
    """Shape (SEQ_LENGTH, FEATURE_DIM_SEQ); columns match FEATURE_ORDER_TRAINING."""
    a = np.asarray(raw)
    if a.ndim != 2:
        raise ValueError("Raw feature matrix must be 2-D (SEQ_LENGTH, features); got shape %s" % (a.shape,))
    if a.shape[1] != config.FEATURE_DIM_SEQ:
        raise ValueError(
            "Raw feature matrix width must be %s (order %s); got %s"
            % (config.FEATURE_DIM_SEQ, list(FEATURE_ORDER_TRAINING), a.shape[1])
        )


def clip_sensors_for_buffer(temp: float, pulse: float, motion: float) -> Tuple[float, float, float]:
    """Clamp to valid physical ranges before building features (keeps scaler stable)."""
    t = float(np.clip(temp, config.SENSOR_TEMP_MIN_C, config.SENSOR_TEMP_MAX_C))
    p = float(np.clip(pulse, config.SENSOR_PULSE_MIN_BPM, config.SENSOR_PULSE_MAX_BPM))
    m = float(np.clip(motion, 0.0, 1.0))
    return t, p, m


def sensors_in_sanity_range(temp: float, pulse: float, motion: float) -> bool:
    """True iff raw readings are inside [20,45], [30,200], [0,1] before clipping."""
    try:
        t, p, m = float(temp), float(pulse), float(motion)
    except (TypeError, ValueError):
        return False
    return (
        config.SENSOR_TEMP_MIN_C <= t <= config.SENSOR_TEMP_MAX_C
        and config.SENSOR_PULSE_MIN_BPM <= p <= config.SENSOR_PULSE_MAX_BPM
        and 0.0 <= m <= 1.0
    )


def safe_class_index(k: Any) -> int:
    """Map arbitrary index to 0..NUM_PAD_CLASSES-1 without crashing."""
    try:
        i = int(k)
    except (TypeError, ValueError):
        return 0
    n = config.NUM_PAD_CLASSES
    if i < 0 or i >= n:
        return 0
    return i


def pad_level_from_index(k: int) -> str:
    i = safe_class_index(k)
    return str(config.PAD_LEVEL_CLASSES[i])


def fallback_pad_level_from_temp(temp_c: float) -> str:
    """
    Rule fallback (same bands as training label_rules).
    HIGH: <35; MEDIUM: [35,35.5); LOW: [35.5,36]; OFF: >36.
    """
    t = float(temp_c)
    if t < 35.0:
        return "HIGH"
    if t < 35.5:
        return "MEDIUM"
    if t <= 36.0:
        return "LOW"
    return "OFF"


def get_model_version_tag(backend: str) -> str:
    """Tag for Firebase/logs: env MODULE2_MODEL_VERSION or MODEL_VERSION_DEFAULT."""
    v = os.environ.get("MODULE2_MODEL_VERSION", "").strip()
    if v:
        return v
    return getattr(config, "MODEL_VERSION_DEFAULT", "tflite_v2")


def validate_scaler_feature_order(scaler: Any) -> None:
    """
    Ensure scaler_features.pkl matches current training feature count and (if present) names.
    Raises ValueError on mismatch.
    """
    expected_n = config.FEATURE_DIM_SEQ
    n = getattr(scaler, "n_features_in_", None)
    if n is not None and int(n) != expected_n:
        raise ValueError(
            "scaler_features.pkl has n_features_in_=%s but training expects %s features "
            "in order %s"
            % (n, expected_n, list(FEATURE_ORDER_TRAINING))
        )
    names = getattr(scaler, "feature_names_in_", None)
    if names is not None and len(names) == expected_n:
        got = [str(x) for x in names]
        exp = list(config.FEATURE_COLS_SEQ)
        if got != exp:
            raise ValueError(
                "Feature order mismatch: scaler feature_names_in_ != config.FEATURE_COLS_SEQ.\n"
                "  scaler: %s\n  config: %s" % (got, exp)
            )


def load_scaler_features_only(path: Optional[str] = None) -> Any:
    """
    Load only ``data/scaler_features.pkl`` (StandardScaler from training). Never calls fit().
    """
    p = os.path.abspath(path or config.SCALER_FEATURES_PATH)
    if not os.path.isfile(p):
        raise FileNotFoundError("Scaler not found: %s" % p)
    with open(p, "rb") as f:
        obj = pickle.load(f)
    if not hasattr(obj, "transform"):
        raise TypeError(
            "scaler_features.pkl must expose transform(); got %s" % type(obj).__name__
        )
    validate_scaler_feature_order(obj)
    return obj


def validate_classifier_output_probs(out: np.ndarray) -> np.ndarray:
    """
    TFLite/Keras softmax output: shape (NUM_PAD_CLASSES,), finite, valid distribution, argmax in bounds.
    Accepts logits (normalizes) or probabilities.
    """
    p = np.asarray(out, dtype=np.float64).reshape(-1)
    n = config.NUM_PAD_CLASSES
    if p.size != n:
        raise ValueError("Classifier output must have shape (%d,), got %s" % (n, p.shape))
    if not np.all(np.isfinite(p)):
        raise ValueError("Non-finite classifier output")
    sm = float(np.sum(p))
    if sm <= 0:
        raise ValueError("Classifier output has non-positive sum")
    # Logits vs probabilities
    if abs(sm - 1.0) > 0.25:
        p = np.exp(p - np.max(p))
        p = p / float(np.sum(p))
    else:
        p = p / sm
    idx = int(np.argmax(p))
    if idx < 0 or idx >= n:
        raise ValueError("Argmax index %s out of range [0, %d)" % (idx, n))
    return p


def validate_sequence_batch_shape(x: np.ndarray, seq_len: int, feat_dim: int) -> None:
    """TFLite / Keras sequence input must be exactly (1, SEQ_LENGTH, FEATURE_DIM_SEQ)."""
    a = np.asarray(x)
    expected = (1, int(seq_len), int(feat_dim))
    if tuple(a.shape) != expected:
        raise ValueError(
            "Model input shape must be %s (batch, SEQ_LENGTH, features); got %s"
            % (expected, tuple(a.shape))
        )


class PadLevelProbabilitySmoother:
    """Average the last ``window`` softmax vectors; return stabilized probabilities."""

    def __init__(self, window: int = 3) -> None:
        self._window = max(1, int(window))
        self._hist: Deque[np.ndarray] = deque(maxlen=self._window)

    def reset(self) -> None:
        self._hist.clear()

    def smooth_proba(self, probs: np.ndarray) -> np.ndarray:
        p = np.asarray(probs, dtype=np.float64).reshape(-1)
        if p.size != config.NUM_PAD_CLASSES:
            raise ValueError("smooth_proba expects %d probs" % config.NUM_PAD_CLASSES)
        self._hist.append(p / max(float(np.sum(p)), 1e-12))
        stacked = np.stack(list(self._hist), axis=0)
        avg = np.mean(stacked, axis=0)
        s = float(np.sum(avg))
        if s <= 0:
            return np.ones(config.NUM_PAD_CLASSES, dtype=np.float64) / config.NUM_PAD_CLASSES
        return avg / s


# Back-compat alias
PadLevelMajoritySmoother = PadLevelProbabilitySmoother
