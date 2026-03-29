"""
Deterministic pad_level from sensors.

Training labels must be a deterministic function of features; otherwise no model can
reach high accuracy (stochastic labels are not predictable from X).
"""
import os
import pickle
from typing import Any, Dict, Optional, Tuple

import numpy as np
import pandas as pd

from . import config

RULE_VERSION = 2
THRESHOLDS_PATH = os.path.join(config.DATA_DIR, "pad_level_score_bins.pkl")


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
    Higher score => more heating demand => higher pad class (toward HIGH).
    Uses small spreads in temp/pulse/motion/demographics so rows are separable even
    when many temperatures are clamped at 34.9 °C.
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
    """Lowest quartile -> OFF; highest quartile -> HIGH."""
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
    payload = {
        "version": RULE_VERSION,
        "q25": q25,
        "q50": q50,
        "q75": q75,
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
    """Overwrite pad_level from heat-demand score + 25/50/75% quantile bins."""
    out = df.copy()
    scores = heat_demand_score_from_dataframe(out)
    q25, q50, q75 = fit_quantile_thresholds(scores)
    y = class_indices_from_scores(scores, q25, q50, q75)
    out[config.COL_PAD_LEVEL] = scores_to_pad_level_strings(y)
    if save_bins:
        save_thresholds(q25, q50, q75)
    return out


def relabel_with_saved_thresholds(df: pd.DataFrame) -> pd.DataFrame:
    """Align pad_level with last saved quantiles (same mapping as training / Firebase rule)."""
    th = load_thresholds()
    if th is None:
        return df
    out = df.copy()
    scores = heat_demand_score_from_dataframe(out)
    y = class_indices_from_scores(scores, th["q25"], th["q50"], th["q75"])
    out[config.COL_PAD_LEVEL] = scores_to_pad_level_strings(y)
    return out


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
    """Rule-based class index (0..3); uses saved quantiles if available."""
    if thresholds is None:
        thresholds = load_thresholds()
    if thresholds is None:
        return 0
    s = heat_demand_score_array(
        np.array([temp], dtype=np.float64),
        np.array([pulse], dtype=np.float64),
        np.array([motion], dtype=np.float64),
        np.array([age], dtype=np.float64),
        np.array([height], dtype=np.float64),
        np.array([weight], dtype=np.float64),
        np.array([gender], dtype=np.float64),
    )[0]
    q25, q50, q75 = thresholds["q25"], thresholds["q50"], thresholds["q75"]
    if s <= q25:
        return 0
    if s <= q50:
        return 1
    if s <= q75:
        return 2
    return 3
