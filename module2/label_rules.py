"""
Deterministic pad_level from body temperature (°C).

Labels are predictable from temp; pulse/motion still appear as features for sequence context.

Rule (PAD_LEVEL_CLASSES order: OFF=0, LOW=1, MEDIUM=2, HIGH=3):
  temp < 35        → HIGH
  35 ≤ temp < 35.5 → MEDIUM
  35.5 ≤ temp ≤ 36 → LOW
  temp > 36        → OFF
"""
import os
import pickle
from typing import Any, Dict, Optional, Tuple, Union

import numpy as np
import pandas as pd

from . import config

RULE_VERSION = 3
THRESHOLDS_PATH = os.path.join(config.DATA_DIR, "pad_level_score_bins.pkl")


def class_indices_from_temperature(temp_c: Union[np.ndarray, float]) -> np.ndarray:
    """
    Vectorized class index 0..3 from °C.
    OFF=0, LOW=1, MEDIUM=2, HIGH=3.
    """
    t = np.asarray(temp_c, dtype=np.float64)
    y = np.zeros(t.shape, dtype=np.int32)
    y[t > 36.0] = 0
    y[(t >= 35.5) & (t <= 36.0)] = 1
    y[(t >= 35.0) & (t < 35.5)] = 2
    y[t < 35.0] = 3
    return y


def pad_level_strings_from_temperature(temp_c: np.ndarray) -> np.ndarray:
    idx = class_indices_from_temperature(temp_c)
    classes = np.array(list(config.PAD_LEVEL_CLASSES))
    return classes[idx.astype(np.int64)]


def heat_demand_score_array(
    temp_c: np.ndarray,
    pulse: np.ndarray,
    motion_01: np.ndarray,
    age: np.ndarray,
    height_cm: np.ndarray,
    weight_kg: np.ndarray,
    gender_01: np.ndarray,
) -> np.ndarray:
    """
    Legacy score (still useful for EDA / non-temperature baselines).
    Higher => more heating demand.
    """
    t = temp_c.astype(np.float64)
    p = pulse.astype(np.float64)
    m = motion_01.astype(np.float64)
    a = age.astype(np.float64)
    h = height_cm.astype(np.float64)
    w = weight_kg.astype(np.float64)
    g = gender_01.astype(np.float64)
    return (
        (36.8 - t) * 15.0
        + (65.0 - p) * 0.08
        + (1.0 - m) * 2.5
        + np.maximum(0.0, 28.0 - a) * 0.03
        + (175.0 - h) * 0.002
        + (72.0 - w) * 0.04
        + (0.5 - g) * 0.15
    )


def heat_demand_score_from_dataframe(df: pd.DataFrame) -> np.ndarray:
    return heat_demand_score_array(
        df[config.COL_TEMP].values,
        df[config.COL_PULSE].values,
        df[config.COL_MOTION].values,
        df[config.COL_AGE].values,
        df[config.COL_HEIGHT_CM].values,
        df[config.COL_WEIGHT_KG].values,
        df[config.COL_GENDER].values,
    )


def class_indices_from_scores(
    scores: np.ndarray, q25: float, q50: float, q75: float
) -> np.ndarray:
    """Deprecated quantile bins (kept for old pickles / tests)."""
    s = scores.astype(np.float64)
    y = np.zeros(len(s), dtype=np.int32)
    y[s <= q25] = 0
    y[(s > q25) & (s <= q50)] = 1
    y[(s > q50) & (s <= q75)] = 2
    y[s > q75] = 3
    return y


def scores_to_pad_level_strings(y: np.ndarray) -> np.ndarray:
    classes = np.array(list(config.PAD_LEVEL_CLASSES))
    return classes[y.astype(np.int64)]


def fit_quantile_thresholds(scores: np.ndarray) -> Tuple[float, float, float]:
    q25, q50, q75 = np.percentile(scores, [25.0, 50.0, 75.0])
    return float(q25), float(q50), float(q75)


def save_thresholds(
    q25: float,
    q50: float,
    q75: float,
    path: str = THRESHOLDS_PATH,
) -> None:
    """Legacy file format; prefer save_rule_metadata for v3."""
    payload = {
        "version": RULE_VERSION,
        "q25": q25,
        "q50": q50,
        "q75": q75,
    }
    with open(path, "wb") as f:
        pickle.dump(payload, f)


def save_rule_metadata(path: str = THRESHOLDS_PATH) -> None:
    """Persist rule version so old quantile pickles are not mistaken for current rules."""
    payload = {
        "version": RULE_VERSION,
        "rule": "temperature_bands",
        "bands_c": {"high": "<35", "medium": "[35,35.5)", "low": "[35.5,36]", "off": ">36"},
    }
    with open(path, "wb") as f:
        pickle.dump(payload, f)


def load_thresholds(path: str = THRESHOLDS_PATH) -> Optional[Dict[str, Any]]:
    if not os.path.isfile(path):
        return None
    with open(path, "rb") as f:
        d = pickle.load(f)
    if d.get("version") != RULE_VERSION:
        return None
    return d


def apply_deterministic_pad_labels(
    df: pd.DataFrame,
    save_bins: bool = True,
) -> pd.DataFrame:
    """Overwrite pad_level from temperature bands."""
    out = df.copy()
    t = pd.to_numeric(out[config.COL_TEMP], errors="coerce").fillna(36.5).values
    y = class_indices_from_temperature(t)
    out[config.COL_PAD_LEVEL] = scores_to_pad_level_strings(y)
    if save_bins:
        save_rule_metadata()
    return out


def relabel_with_saved_thresholds(df: pd.DataFrame) -> pd.DataFrame:
    """Same as training: temperature bands (ignores old quantile pickles)."""
    return apply_deterministic_pad_labels(df, save_bins=False)


def pad_class_from_raw_features(
    temp: float,
    pulse: float,
    motion: float,
    age: float,
    height: float,
    weight: float,
    gender: float,
    thresholds: Optional[Dict[str, Any]] = None,
) -> int:
    """Rule-based class index from body temperature (other args ignored)."""
    del pulse, motion, age, height, weight, gender, thresholds
    y = class_indices_from_temperature(np.array([float(temp)], dtype=np.float64))
    return int(y[0])
