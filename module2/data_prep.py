"""
Phase 1 — Data preparation (continuous time-series, no session_id).

- Sort by timestamp (or stable row order if timestamps are non-numeric / unparseable)
- temp_step = diff(temp), pulse_step = diff(pulse), clip & fill NaN
- StandardScaler fit on all raw timestep rows (FEATURE_COLS_SEQ), then sliding windows
  on the scaled matrix (matches inference: raw buffer → scale → (1, SEQ_LENGTH, 10))
"""

from __future__ import annotations

import os
import pickle
from typing import Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler, StandardScaler

from . import config


def _append_temperature_coverage_synthetic(df: pd.DataFrame) -> pd.DataFrame:
    """
    Append stratified synthetic rows (33–38 °C) so all label bands exist when real data
    is narrow. Disable with MODULE2_APPEND_TEMP_COVERAGE=0. Size: MODULE2_SYNTHETIC_N (default 24000).
    """
    raw = os.environ.get("MODULE2_APPEND_TEMP_COVERAGE", "1").strip().lower()
    if raw in ("0", "false", "no", "off"):
        return df
    try:
        n = int(
            os.environ.get(
                "MODULE2_SYNTHETIC_N",
                str(getattr(config, "DEFAULT_SYNTHETIC_APPEND_ROWS", 24_000)),
            )
        )
    except ValueError:
        n = int(getattr(config, "DEFAULT_SYNTHETIC_APPEND_ROWS", 24_000))
    if n <= 0:
        return df

    from .synthetic_dataset import generate_temperature_coverage_synthetic

    try:
        col = df[config.COL_TIMESTAMP]
        tmax = pd.to_numeric(col, errors="coerce").max()
        start = float(tmax) + 1.0 if np.isfinite(tmax) else 1.0e9
    except Exception:
        start = 1.0e9

    syn = generate_temperature_coverage_synthetic(
        n_rows=n,
        seed=config.SHUFFLE_SEED,
        timestamp_start=start,
    )
    for c in df.columns:
        if c not in syn.columns:
            syn[c] = np.nan
    syn = syn[df.columns]
    out = pd.concat([df, syn], ignore_index=True)
    print(
        "Appended %s synthetic rows (temp stratified ~%s–%s °C); combined rows: %s. "
        "Set MODULE2_APPEND_TEMP_COVERAGE=0 to skip (e.g. pre-merged CSV)."
        % (
            n,
            getattr(config, "SYNTHETIC_TEMP_RANGE_MIN_C", 33),
            getattr(config, "SYNTHETIC_TEMP_RANGE_MAX_C", 38),
            len(out),
        )
    )
    return out


def _clip_and_report_body_temperature(df):
    """Clip training temps to config band; print min/max/mean and out-of-range counts."""
    df = df.copy()
    t = pd.to_numeric(df[config.COL_TEMP], errors="coerce")
    lo = float(config.TEMP_TRAINING_CLIP_MIN_C)
    hi = float(config.TEMP_TRAINING_CLIP_MAX_C)
    n = len(t)
    n_nan = int(t.isna().sum())
    valid = t.dropna()
    if len(valid):
        print(
            "Temperature (raw): min=%.3f max=%.3f mean=%.3f °C | NaN rows=%s / %s"
            % (float(valid.min()), float(valid.max()), float(valid.mean()), n_nan, n)
        )
    else:
        print("Temperature column: all NaN")
    out_mask = (t < lo) | (t > hi)
    n_out = int(out_mask.sum())
    if n_out:
        print(
            "  Clipping %s values to [%.1f, %.1f] °C (training normalization check)"
            % (n_out, lo, hi)
        )
    t = t.clip(lo, hi)
    df[config.COL_TEMP] = t.fillna(36.5)
    return df


def balance_sequence_windows(
    X_seq: np.ndarray,
    y_seq: np.ndarray,
    seed: Optional[int] = None,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Oversample per-class so each class has the same count (max class frequency).
    Shuffles the combined set (IID batches, not pure chronological).
    """
    rng = np.random.RandomState(seed if seed is not None else config.SHUFFLE_SEED)
    n_classes = config.NUM_PAD_CLASSES
    counts = np.bincount(y_seq.astype(np.int64), minlength=n_classes)
    if np.any(counts == 0):
        missing = [i for i in range(n_classes) if counts[i] == 0]
        raise ValueError(
            "Cannot balance: no samples for class index(es) %s. "
            "Check temperature distribution vs label bands (re-run with more data or adjust CSV)."
            % missing
        )
    n_target = int(counts.max())
    parts_X: list = []
    parts_y: list = []
    for c in range(n_classes):
        idx = np.where(y_seq == c)[0]
        if len(idx) < n_target:
            extra = rng.choice(idx, size=n_target - len(idx), replace=True)
            idx = np.concatenate([idx, extra])
        else:
            idx = rng.choice(idx, size=n_target, replace=False)
        rng.shuffle(idx)
        parts_X.append(X_seq[idx])
        parts_y.append(y_seq[idx])
    X_bal = np.vstack(parts_X)
    y_bal = np.concatenate(parts_y)
    perm = rng.permutation(len(y_bal))
    return X_bal[perm].astype(np.float32), y_bal[perm].astype(np.int32)


def _read_tabular(path):
    ext = os.path.splitext(path)[1].lower()
    if ext in (".xlsx", ".xls"):
        return pd.read_excel(path)
    return pd.read_csv(path)


def standardize_dataset_columns(df):
    df = df.copy()

    if config.COL_TEMP not in df.columns and "body_temp" in df.columns:
        df[config.COL_TEMP] = pd.to_numeric(df["body_temp"], errors="coerce")

    if config.COL_MOTION not in df.columns and "motion_level" in df.columns:
        df[config.COL_MOTION] = pd.to_numeric(df["motion_level"], errors="coerce")

    return df


def _coerce_timestamp(df):
    """Stable time order: parse timestamps when possible, else preserve original row order."""
    df = df.copy()
    df["_orig_ix"] = np.arange(len(df), dtype=np.int64)
    if config.COL_TIMESTAMP not in df.columns:
        df[config.COL_TIMESTAMP] = df["_orig_ix"].astype(np.float64)
    else:
        col = df[config.COL_TIMESTAMP]
        if pd.api.types.is_numeric_dtype(col):
            pass
        else:
            parsed = pd.to_datetime(col, errors="coerce")
            if parsed.notna().mean() > 0.5:
                df[config.COL_TIMESTAMP] = parsed.astype("int64") // 10**9
            else:
                df[config.COL_TIMESTAMP] = df["_orig_ix"].astype(np.float64)
    df = (
        df.sort_values([config.COL_TIMESTAMP, "_orig_ix"])
        .drop(columns=["_orig_ix"])
        .reset_index(drop=True)
    )
    return df


def ensure_demographic_columns(df):
    if config.COL_AGE not in df.columns:
        df[config.COL_AGE] = config.DEFAULT_AGE_YEARS
    if config.COL_HEIGHT_CM not in df.columns:
        df[config.COL_HEIGHT_CM] = config.DEFAULT_HEIGHT_CM
    if config.COL_WEIGHT_KG not in df.columns:
        df[config.COL_WEIGHT_KG] = config.DEFAULT_WEIGHT_KG
    if config.COL_GENDER not in df.columns:
        df[config.COL_GENDER] = config.DEFAULT_GENDER_0_1

    return df


def read_dataset_file(path=None, sync_labels_from_rules: bool = True):
    path = path or config.DATASET_PATH

    df = _read_tabular(path)
    df = standardize_dataset_columns(df)
    df = _append_temperature_coverage_synthetic(df)
    df = _coerce_timestamp(df)
    df = ensure_demographic_columns(df)

    df[config.COL_TEMP] = pd.to_numeric(df[config.COL_TEMP], errors="coerce")
    df = _clip_and_report_body_temperature(df)
    df[config.COL_TEMP_DELTA] = df[config.COL_TEMP] - 36.5

    if sync_labels_from_rules:
        from .label_rules import apply_deterministic_pad_labels

        df = apply_deterministic_pad_labels(df, save_bins=True)

    return df


def enforce_time_series_order(df):
    return df.sort_values(config.COL_TIMESTAMP).reset_index(drop=True)


def add_time_step_derivatives(df):
    """
    Consecutive diffs (no session grouping). Clip and zero-fill first row / NaNs.
    """
    df = df.copy()
    t = pd.to_numeric(df[config.COL_TEMP], errors="coerce")
    p = pd.to_numeric(df[config.COL_PULSE], errors="coerce")
    df[config.COL_TEMP_STEP] = t.diff().clip(-1.0, 1.0).fillna(0.0)
    df[config.COL_PULSE_STEP] = p.diff().clip(-10.0, 10.0).fillna(0.0)
    return df


# Back-compat alias
add_session_time_derivatives = add_time_step_derivatives


def sliding_windows(X, y, seq_len):
    X_list, y_list = [], []
    n = len(X)
    if n < seq_len:
        raise ValueError("Not enough data for sequence")
    for t in range(seq_len - 1, n):
        X_list.append(X[t - seq_len + 1 : t + 1])
        y_list.append(y[t])
    return np.array(X_list, dtype=np.float32), np.array(y_list, dtype=np.int32)


def run():
    print("=== DATA PREP (continuous time-series) ===")
    print("Dataset file:", os.path.abspath(config.DATASET_PATH))

    df = read_dataset_file(sync_labels_from_rules=True)
    df = enforce_time_series_order(df)
    df = add_time_step_derivatives(df)

    print("Dataset shape:", df.shape)
    print(
        "Feature order (10):",
        list(config.FEATURE_COLS_SEQ),
    )

    y_raw = df[config.COL_PAD_LEVEL].astype(str).str.upper().str.strip()
    class_to_idx = {c: i for i, c in enumerate(config.PAD_LEVEL_CLASSES)}
    y = y_raw.map(lambda x: class_to_idx.get(x, 0)).astype(np.int32).values

    print("Class distribution (timestep labels, before windows):")
    for i, name in enumerate(config.PAD_LEVEL_CLASSES):
        n_i = int(np.sum(y == i))
        print("  %s: %s (%.2f%%)" % (name, n_i, 100.0 * n_i / max(len(y), 1)))

    X_raw = df[config.FEATURE_COLS_SEQ].replace([np.inf, -np.inf], np.nan).fillna(0.0)
    X_raw = X_raw.values.astype(np.float64)
    scaler_X = StandardScaler()
    scaler_X.fit(X_raw)
    X_scaled = scaler_X.transform(X_raw).astype(np.float32)

    with open(config.SCALER_FEATURES_PATH, "wb") as f:
        pickle.dump(scaler_X, f)
    print("Saved scaler:", config.SCALER_FEATURES_PATH)

    X_seq, y_seq = sliding_windows(X_scaled, y, config.SEQ_LENGTH)
    print("Sequence tensors (before balance):", X_seq.shape, y_seq.shape)
    print("Class distribution (sequence endpoints, before balance):")
    for i, name in enumerate(config.PAD_LEVEL_CLASSES):
        n_i = int(np.sum(y_seq == i))
        print("  %s: %s (%.2f%%)" % (name, n_i, 100.0 * n_i / max(len(y_seq), 1)))

    X_seq, y_seq = balance_sequence_windows(X_seq, y_seq, seed=config.SHUFFLE_SEED)
    print("Sequence tensors (class-balanced):", X_seq.shape, y_seq.shape)
    print("Class distribution (after balance):")
    for i, name in enumerate(config.PAD_LEVEL_CLASSES):
        n_i = int(np.sum(y_seq == i))
        print("  %s: %s (%.2f%%)" % (name, n_i, 100.0 * n_i / max(len(y_seq), 1)))

    np.save(os.path.join(config.DATA_DIR, "X_seq_pad.npy"), X_seq)
    np.save(os.path.join(config.DATA_DIR, "y_pad_class_seq.npy"), y_seq)
    np.save(os.path.join(config.DATA_DIR, "X_seq.npy"), X_seq)
    np.save(os.path.join(config.DATA_DIR, "y_seq.npy"), y_seq)

    np.save(os.path.join(config.DATA_DIR, "X_scaled_timeseries.npy"), X_scaled)
    np.save(os.path.join(config.DATA_DIR, "y_pad_class_ordered.npy"), y)

    rng = np.random.RandomState(config.SHUFFLE_SEED)
    perm = rng.permutation(len(df))
    df_shuf = df.iloc[perm].reset_index(drop=True)
    y_shuf = (
        df_shuf[config.COL_PAD_LEVEL]
        .astype(str)
        .str.strip()
        .str.upper()
        .map(lambda s: class_to_idx.get(s, 0))
        .astype(np.int32)
        .values
    )
    X_flat = df_shuf[config.FEATURE_COLS].values.astype(np.float32)
    scaler_flat = MinMaxScaler()
    X_scaled_flat = scaler_flat.fit_transform(X_flat).astype(np.float32)
    np.save(os.path.join(config.DATA_DIR, "X_scaled.npy"), X_scaled_flat)
    np.save(os.path.join(config.DATA_DIR, "y_pad_class.npy"), y_shuf)
    print("Saved legacy flat arrays: X_scaled.npy, y_pad_class.npy (shuffled 8-D)")

    return X_seq, y_seq, scaler_X


if __name__ == "__main__":
    run()
