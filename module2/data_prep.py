"""
Phase 1 — Data preparation (time-series aware).

Sequences for LSTM+DNN are built from rows sorted by (session_id, timestamp) per session.
Per-step Δtemp / Δpulse capture short-term dynamics. Flat shuffled arrays use base 8
features only for legacy compatibility where needed.
"""
import os
import pickle
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.preprocessing import MinMaxScaler, StandardScaler

from . import config

# Columns allowed on disk and used for training (no pad PWM, no raw motion_level).
TRAINING_EXPORT_COLUMNS = [
    config.COL_TIMESTAMP,
    config.COL_TEMP,
    config.COL_PULSE,
    config.COL_MOTION,
    config.COL_AGE,
    config.COL_HEIGHT_CM,
    config.COL_WEIGHT_KG,
    config.COL_GENDER,
    config.COL_PAD_LEVEL,
    "session_id",
]


def finalize_training_dataframe(df):
    """
    Strip legacy/duplicate columns: never keep pad1/pad2, never keep both body_temp and
    body_temperature_C, map motion_level -> motion_level_0_1 (0/1) and drop motion_level.
    """
    df = df.copy()

    for c in ("pad1_pwm_0_100", "pad2_pwm_0_100"):
        if c in df.columns:
            df = df.drop(columns=[c])

    if "body_temp" in df.columns:
        if config.COL_TEMP not in df.columns:
            df[config.COL_TEMP] = pd.to_numeric(df["body_temp"], errors="coerce")
        df = df.drop(columns=["body_temp"])

    if "motion_level" in df.columns:
        m = pd.to_numeric(df["motion_level"], errors="coerce").fillna(0.0)
        df[config.COL_MOTION] = (m >= 0.5).astype(float)
        df = df.drop(columns=["motion_level"])

    if config.COL_MOTION not in df.columns:
        raise ValueError("Dataset must end up with column " + config.COL_MOTION)

    m = pd.to_numeric(df[config.COL_MOTION], errors="coerce").fillna(0.0)
    df[config.COL_MOTION] = (m >= 0.5).astype(float)

    for col in TRAINING_EXPORT_COLUMNS:
        if col not in df.columns:
            if col == "session_id":
                df["session_id"] = 0
            else:
                raise ValueError(f"Missing required column after cleanup: {col}")

    return df[TRAINING_EXPORT_COLUMNS].copy()


def load_and_clean_file(path):
    """Load any legacy CSV and rewrite to TRAINING_EXPORT_COLUMNS only."""
    df = _read_tabular(path)
    df = standardize_dataset_columns(df)
    df = _coerce_timestamp(df)
    df = ensure_demographic_columns(df)
    return finalize_training_dataframe(df)


def _read_tabular(path):
    ext = os.path.splitext(path)[1].lower()
    if ext in (".xlsx", ".xls"):
        return pd.read_excel(path)
    return pd.read_csv(path)


def standardize_dataset_columns(df):
    """Map legacy names into canonical columns; does not drop duplicates — finalize_training_dataframe does."""
    df = df.copy()
    if config.COL_TEMP not in df.columns and "body_temp" in df.columns:
        df[config.COL_TEMP] = pd.to_numeric(df["body_temp"], errors="coerce")
    if config.COL_MOTION not in df.columns and "motion_level" in df.columns:
        df[config.COL_MOTION] = pd.to_numeric(df["motion_level"], errors="coerce")
    return df


def _coerce_timestamp(df):
    if config.COL_TIMESTAMP not in df.columns:
        df[config.COL_TIMESTAMP] = np.arange(len(df), dtype=np.float64)
        return df
    ts = df[config.COL_TIMESTAMP]
    if pd.api.types.is_datetime64_any_dtype(ts):
        df = df.sort_values(config.COL_TIMESTAMP, kind="mergesort").reset_index(drop=True)
        return df
    ts_num = pd.to_numeric(ts, errors="coerce")
    if ts_num.notna().sum() >= max(1, len(df) // 2):
        df = df.assign(**{config.COL_TIMESTAMP: ts_num})
        df = df.sort_values(config.COL_TIMESTAMP, kind="mergesort").reset_index(drop=True)
    return df


def read_dataset_file(path=None, sync_labels_from_rules: bool = True):
    """
    Load CSV. If ``data/pad_level_score_bins.pkl`` exists (after training), optionally
    recompute ``pad_level`` from the heat-demand rule so CSV matches the model.
    Pass ``sync_labels_from_rules=False`` before fitting new quantiles in training.
    """
    path = path or config.DATASET_PATH
    df = _read_tabular(path)
    df = standardize_dataset_columns(df)
    df = _coerce_timestamp(df)
    df = ensure_demographic_columns(df)
    df = finalize_training_dataframe(df)
    df[config.COL_TEMP_DELTA] = pd.to_numeric(df[config.COL_TEMP], errors="coerce") - 36.5
    if sync_labels_from_rules:
        from .label_rules import relabel_with_saved_thresholds

        df = relabel_with_saved_thresholds(df)
    return df


def _to_gender_numeric(v):
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        s = v.strip().lower()
        if s in ("male", "m", "man", "boy"):
            return 1.0
        if s in ("female", "f", "woman", "girl"):
            return 0.0
    return config.DEFAULT_GENDER_0_1


def ensure_demographic_columns(df):
    if config.COL_AGE not in df.columns:
        df[config.COL_AGE] = config.DEFAULT_AGE_YEARS
    if config.COL_HEIGHT_CM not in df.columns:
        df[config.COL_HEIGHT_CM] = config.DEFAULT_HEIGHT_CM
    if config.COL_WEIGHT_KG not in df.columns:
        df[config.COL_WEIGHT_KG] = config.DEFAULT_WEIGHT_KG
    if config.COL_GENDER not in df.columns:
        if "gender" in df.columns:
            df[config.COL_GENDER] = df["gender"].apply(_to_gender_numeric)
        else:
            df[config.COL_GENDER] = config.DEFAULT_GENDER_0_1

    for col in (config.COL_AGE, config.COL_HEIGHT_CM, config.COL_WEIGHT_KG):
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df[config.COL_GENDER] = df[config.COL_GENDER].apply(_to_gender_numeric)

    df[config.COL_AGE] = df[config.COL_AGE].fillna(config.DEFAULT_AGE_YEARS)
    df[config.COL_HEIGHT_CM] = df[config.COL_HEIGHT_CM].fillna(config.DEFAULT_HEIGHT_CM)
    df[config.COL_WEIGHT_KG] = df[config.COL_WEIGHT_KG].fillna(config.DEFAULT_WEIGHT_KG)
    df[config.COL_GENDER] = df[config.COL_GENDER].fillna(config.DEFAULT_GENDER_0_1)

    if config.COL_MOTION in df.columns:
        m = pd.to_numeric(df[config.COL_MOTION], errors="coerce").fillna(0.0)
        df[config.COL_MOTION] = (m >= 0.5).astype(float)
    return df


def _dataset_summary_and_plots(df):
    print("Dataset shape:", df.shape)
    print(df[config.FEATURE_COLS + [config.COL_PAD_LEVEL]].describe(include="all"))
    print("\nMissing:", df.isnull().sum())

    fig, ax = plt.subplots(figsize=(12, 4))
    ax.plot(df.index, df[config.COL_TEMP], alpha=0.7)
    ax.set_xlabel("Row index (file order before shuffle)")
    ax.set_ylabel("Body temperature (°C)")
    ax.set_title("Temperature (file order)")
    plt.tight_layout()
    plt.savefig(os.path.join(config.PLOTS_DIR, "01_temperature_over_time.png"), dpi=120)
    plt.close()
    print("Saved: 01_temperature_over_time.png")

    pl_num = pd.Categorical(df[config.COL_PAD_LEVEL].astype(str).str.upper().str.strip()).codes
    fig, ax = plt.subplots(figsize=(8, 5))
    sc = ax.scatter(df[config.COL_TEMP], pl_num, alpha=0.35, s=8, c=pl_num, cmap="viridis")
    ax.set_xlabel("Body temperature (°C)")
    ax.set_ylabel("pad_level (encoded)")
    ax.set_title("Temperature vs pad_level")
    plt.colorbar(sc, ax=ax, label="class code")
    plt.tight_layout()
    plt.savefig(os.path.join(config.PLOTS_DIR, "02_temp_vs_pad_level.png"), dpi=120)
    plt.close()
    print("Saved: 02_temp_vs_pad_level.png")

    n_features = len(config.FEATURE_COLS)
    n_cols = 3
    n_rows = (n_features + n_cols - 1) // n_cols
    fig, axes = plt.subplots(n_rows, n_cols, figsize=(12, 4 * n_rows))
    axes = np.atleast_1d(axes).reshape(n_rows, n_cols)
    for i, col in enumerate(config.FEATURE_COLS):
        r, c = divmod(i, n_cols)
        axes[r, c].hist(df[col].dropna(), bins=50, edgecolor="black", alpha=0.7)
        axes[r, c].set_title(col)
    for j in range(n_features, n_rows * n_cols):
        r, c = divmod(j, n_cols)
        axes[r, c].axis("off")
    plt.tight_layout()
    plt.savefig(os.path.join(config.PLOTS_DIR, "03_distributions.png"), dpi=120)
    plt.close()
    print("Saved: 03_distributions.png")


def load_and_explore():
    """Load CSV; if score bins exist, relabel to match the trained rule."""
    df = read_dataset_file(sync_labels_from_rules=True)
    _dataset_summary_and_plots(df)
    return df


def enforce_time_series_order(df: pd.DataFrame) -> pd.DataFrame:
    """Sort by session then timestamp so each session is a proper time series."""
    return df.sort_values(["session_id", config.COL_TIMESTAMP], kind="mergesort").reset_index(
        drop=True
    )


def add_session_time_derivatives(df: pd.DataFrame) -> pd.DataFrame:
    """
    Within each session, set temp_delta_step / pulse_delta_step to consecutive differences.
    First row of each session has zeros (no prior sample).
    """
    df = df.copy()
    df[config.COL_TEMP_DELTA_STEP] = 0.0
    df[config.COL_PULSE_DELTA_STEP] = 0.0
    for _, g in df.groupby("session_id", sort=False):
        g = g.sort_values(config.COL_TIMESTAMP, kind="mergesort")
        idx = g.index.to_numpy()
        t = g[config.COL_TEMP].to_numpy(dtype=np.float64)
        p = g[config.COL_PULSE].to_numpy(dtype=np.float64)
        for k in range(1, len(idx)):
            df.at[idx[k], config.COL_TEMP_DELTA_STEP] = t[k] - t[k - 1]
            df.at[idx[k], config.COL_PULSE_DELTA_STEP] = p[k] - p[k - 1]
    return df


def _sliding_windows_per_session(X, y, session_ids, seq_len):
    """
    Build (samples, seq_len, n_features) and labels from time-ordered scaled rows.
    One window ends at timestep t; label is pad_level at t.
    """
    X_list, y_list = [], []
    for sid in np.unique(session_ids):
        m = session_ids == sid
        Xs = X[m]
        ys = y[m]
        n = len(Xs)
        if n < seq_len:
            continue
        for t in range(seq_len - 1, n):
            X_list.append(Xs[t - seq_len + 1 : t + 1])
            y_list.append(ys[t])
    if not X_list:
        raise ValueError(
            "No LSTM windows: every session is shorter than SEQ_LENGTH=%s. "
            "Lower SEQ_LENGTH in config or add longer sessions." % seq_len
        )
    return np.stack(X_list, axis=0).astype(np.float32), np.array(y_list, dtype=np.int32)


def run():
    print("Using dataset file:", os.path.abspath(config.DATASET_PATH))
    from .label_rules import apply_deterministic_pad_labels

    df = read_dataset_file(sync_labels_from_rules=False)
    print(
        "Relabeling pad_level: stochastic CSV labels are replaced by a deterministic "
        "heat-demand score and quartile bins (required for learnable accuracy)."
    )
    df = apply_deterministic_pad_labels(df, save_bins=True)
    print("pad_level counts (relabeled):", df[config.COL_PAD_LEVEL].astype(str).str.upper().value_counts().to_dict())
    _dataset_summary_and_plots(df)

    y_raw = (
        df[config.COL_PAD_LEVEL]
        .astype(str)
        .str.strip()
        .str.upper()
    )
    class_to_idx = {c: i for i, c in enumerate(config.PAD_LEVEL_CLASSES)}
    y_int = y_raw.map(lambda s: class_to_idx.get(s, 0)).astype(np.int32)

    df_ord = enforce_time_series_order(df)
    df_ord = add_session_time_derivatives(df_ord)
    print(
        "Time-series order: rows sorted by (session_id, timestamp); "
        "added per-session Δtemp / Δpulse for LSTM input."
    )

    y_ord = (
        df_ord[config.COL_PAD_LEVEL]
        .astype(str)
        .str.strip()
        .str.upper()
        .map(lambda s: class_to_idx.get(s, 0))
        .astype(np.int32)
        .values
    )

    scaler_X = StandardScaler()
    scaler_X.fit(df_ord[config.FEATURE_COLS_SEQ].values.astype(np.float64))
    X_ord_scaled = scaler_X.transform(
        df_ord[config.FEATURE_COLS_SEQ].values.astype(np.float64)
    ).astype(np.float32)
    session_ids = df_ord["session_id"].values
    X_seq_pad, y_pad_seq = _sliding_windows_per_session(
        X_ord_scaled, y_ord, session_ids, config.SEQ_LENGTH
    )
    np.save(os.path.join(config.DATA_DIR, "X_seq_pad.npy"), X_seq_pad)
    np.save(os.path.join(config.DATA_DIR, "y_pad_class_seq.npy"), y_pad_seq)
    print(
        "Saved X_seq_pad.npy",
        X_seq_pad.shape,
        "| y_pad_class_seq.npy",
        y_pad_seq.shape,
        "(time-series LSTM+DNN,",
        config.FEATURE_DIM_SEQ,
        "channels per step)",
    )

    with open(config.SCALER_FEATURES_PATH, "wb") as f:
        pickle.dump(scaler_X, f)
    print(
        "Saved scaler to",
        config.SCALER_FEATURES_PATH,
        "(StandardScaler, %d features: base + Δtemp/Δpulse per step)" % config.FEATURE_DIM_SEQ,
    )

    np.save(os.path.join(config.DATA_DIR, "X_scaled_timeseries.npy"), X_ord_scaled)
    np.save(os.path.join(config.DATA_DIR, "y_pad_class_ordered.npy"), y_ord)
    print(
        "Saved X_scaled_timeseries.npy (ordered, %d-D) | y_pad_class_ordered.npy"
        % config.FEATURE_DIM_SEQ
    )

    rng = np.random.RandomState(config.SHUFFLE_SEED)
    perm = rng.permutation(len(df))
    df_shuf = df.iloc[perm].reset_index(drop=True)
    y_shuf = y_int.iloc[perm].reset_index(drop=True)
    X_flat = df_shuf[config.FEATURE_COLS].values.astype(np.float32)
    scaler_flat = MinMaxScaler()
    X_scaled_flat = scaler_flat.fit_transform(X_flat).astype(np.float32)
    np.save(os.path.join(config.DATA_DIR, "X_scaled.npy"), X_scaled_flat)
    np.save(os.path.join(config.DATA_DIR, "y_pad_class.npy"), y_shuf.to_numpy())
    print(
        "Saved X_scaled.npy (shuffled, 8-D legacy) | y_pad_class.npy — pad_level counts:",
        dict(zip(*np.unique(y_shuf.to_numpy(), return_counts=True))),
    )
    return X_ord_scaled, y_ord, scaler_X
