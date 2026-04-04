"""
Synthetic vest rows: temperature coverage 33–38 °C + realistic pulse/motion.

Combined with real CSV in data_prep (see ``append_temperature_coverage_synthetic``) or via CLI.
"""
from __future__ import annotations

import argparse
import os
from typing import Optional

import numpy as np
import pandas as pd

from . import config

# Bands align with label_rules.class_indices_from_temperature (training labels applied after merge)
# HIGH: T < 35  |  MEDIUM: [35, 35.5)  |  LOW: [35.5, 36]  |  OFF: T > 36


def _realistic_pulse_bpm(temp_c: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """Slightly higher pulse when cold (stress / shivering); typical resting when warm."""
    t = temp_c.astype(np.float64)
    base = 68.0 + np.clip(36.0 - t, -4.0, 10.0) * 1.15
    noise = rng.normal(0.0, 4.8, size=t.shape)
    p = base + noise
    return np.clip(p, 52.0, 125.0)


def _realistic_motion(rng: np.random.Generator, n: int) -> np.ndarray:
    """Binary motion; ~42% active (typical mixed activity)."""
    return rng.random(n) < 0.42


def generate_temperature_coverage_synthetic(
    n_rows: int,
    seed: int = 42,
    timestamp_start: Optional[float] = None,
) -> pd.DataFrame:
    """
    Stratified samples so each pad_level band gets n_rows//4 rows (approximately).
    Temperature spans [33, 38] °C with sub-ranges mapped to HIGH / MEDIUM / LOW / OFF.
    """
    rng = np.random.default_rng(seed)
    n_rows = int(max(n_rows, 4))
    t_lo = float(getattr(config, "SYNTHETIC_TEMP_RANGE_MIN_C", 33.0))
    t_hi = float(getattr(config, "SYNTHETIC_TEMP_RANGE_MAX_C", 38.0))
    t_lo = min(t_lo, 34.9)
    per = n_rows // 4
    rem = n_rows - 4 * per
    counts = [per + (1 if rem > i else 0) for i in range(4)]

    # HIGH: [t_lo, 35) — label_rules: T < 35 → HIGH
    t_high = rng.uniform(t_lo, 34.999, size=counts[0])
    # MEDIUM: [35, 35.5)
    t_med = rng.uniform(35.0, 35.499, size=counts[1])
    # LOW: [35.5, 36]
    t_low = rng.uniform(35.5, 36.0, size=counts[2])
    # OFF: (36, t_hi] — label_rules: T > 36 → OFF
    off_hi = max(36.002, t_hi)
    t_off = rng.uniform(36.001, off_hi, size=counts[3])

    t_all = np.concatenate([t_high, t_med, t_low, t_off])
    rng.shuffle(t_all)
    n = len(t_all)

    pulse = _realistic_pulse_bpm(t_all, rng)
    motion = _realistic_motion(rng, n).astype(np.float64)
    age = rng.uniform(14.0, 82.0, size=n)
    h_cm = rng.uniform(152.0, 192.0, size=n)
    w_kg = rng.uniform(45.0, 105.0, size=n)
    gender = rng.choice([0.0, 1.0], size=n)

    if timestamp_start is None:
        ts = np.arange(n, dtype=np.float64) + 1.0e9
    else:
        ts = timestamp_start + np.arange(n, dtype=np.float64)

    return pd.DataFrame(
        {
            config.COL_TIMESTAMP: ts,
            config.COL_TEMP: t_all.astype(np.float64),
            config.COL_PULSE: pulse.astype(np.float64),
            config.COL_MOTION: motion,
            config.COL_AGE: age,
            config.COL_HEIGHT_CM: h_cm,
            config.COL_WEIGHT_KG: w_kg,
            config.COL_GENDER: gender,
            config.COL_PAD_LEVEL: np.full(n, "OFF", dtype=object),
        }
    )


def merge_user_with_temperature_synthetic(
    user_path: str,
    out_path: str,
    n_synthetic: int = 24_000,
    seed: int = 42,
) -> str:
    """
    Write a combined CSV: synthetic coverage + existing user rows.
    Re-applies deterministic temperature labels on the full table.
    """
    from .data_prep import (
        _coerce_timestamp,
        _read_tabular,
        ensure_demographic_columns,
        standardize_dataset_columns,
    )
    from .label_rules import apply_deterministic_pad_labels

    syn = generate_temperature_coverage_synthetic(n_synthetic, seed=seed)
    if not os.path.isfile(user_path):
        syn.to_csv(out_path, index=False)
        combined = pd.read_csv(out_path)
        combined = apply_deterministic_pad_labels(combined, save_bins=True)
        combined.to_csv(out_path, index=False)
        return out_path

    raw = _read_tabular(user_path)
    raw = standardize_dataset_columns(raw)
    raw = _coerce_timestamp(raw)
    raw = ensure_demographic_columns(raw)

    try:
        tmax = pd.to_numeric(raw[config.COL_TIMESTAMP], errors="coerce").max()
        start = float(tmax) + 1.0 if np.isfinite(tmax) else 1.0e9
    except Exception:
        start = 1.0e9
    syn = generate_temperature_coverage_synthetic(n_synthetic, seed=seed, timestamp_start=start)

    syn_u = ensure_demographic_columns(syn)
    combined = pd.concat([raw, syn_u], ignore_index=True)
    combined.to_csv(out_path, index=False)
    combined = pd.read_csv(out_path)
    combined = apply_deterministic_pad_labels(combined, save_bins=True)
    combined.to_csv(out_path, index=False)
    return out_path


# --- legacy session-based generator (kept for old scripts) ---

_PAD_LABEL_TO_HEAT = {
    "OFF": 0.0,
    "LOW": 0.25,
    "MEDIUM": 0.5,
    "HIGH": 0.85,
}


def _pick_pad_level_placeholder() -> str:
    return "MEDIUM"


def generate_synthetic_dataframe(
    n_sessions: int = 96,
    steps_per_session: int = 320,
    seed: int = 42,
) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows = []
    global_ts = 0
    for _ in range(n_sessions):
        T = float(rng.uniform(35.5, 37.0))
        age = float(rng.uniform(16.0, 78.0))
        h_cm = float(rng.uniform(150.0, 190.0))
        w_kg = float(rng.uniform(48.0, 98.0))
        gender = float(rng.choice([0.0, 1.0]))
        pulse_base = float(rng.integers(58, 102))

        for _ in range(steps_per_session):
            motion_bin = float(rng.choice([0, 1]))
            pulse = float(np.clip(pulse_base + rng.normal(0, 4.5), 48, 118))
            pad_label = _pick_pad_level_placeholder()
            heat_frac = _PAD_LABEL_TO_HEAT.get(pad_label, 0.0)

            heating = 0.028 * heat_frac * (9.0 + 0.05 * (70.0 - age / 78.0 * 20.0))
            cooling = (0.012 + 0.035 * motion_bin) * (T - 18.5)
            T = T + heating - cooling + float(rng.normal(0, 0.045))
            T = float(np.clip(T, 34.9, 38.8))

            rows.append(
                {
                    config.COL_TIMESTAMP: global_ts,
                    config.COL_TEMP: T,
                    config.COL_PULSE: pulse,
                    config.COL_MOTION: motion_bin,
                    config.COL_AGE: age,
                    config.COL_HEIGHT_CM: h_cm,
                    config.COL_WEIGHT_KG: w_kg,
                    config.COL_GENDER: gender,
                    config.COL_PAD_LEVEL: pad_label,
                }
            )
            global_ts += 1

    return pd.DataFrame(rows)


def merge_user_and_synthetic(
    user_path: str,
    out_path: str,
    n_sessions: int = 96,
    steps_per_session: int = 320,
    seed: int = 42,
) -> str:
    from .data_prep import (
        _coerce_timestamp,
        _read_tabular,
        ensure_demographic_columns,
        standardize_dataset_columns,
    )

    syn = generate_synthetic_dataframe(
        n_sessions=n_sessions, steps_per_session=steps_per_session, seed=seed
    )
    syn_u = ensure_demographic_columns(syn)

    if not os.path.isfile(user_path):
        syn_u.to_csv(out_path, index=False)
        from .label_rules import apply_deterministic_pad_labels

        combined = pd.read_csv(out_path)
        combined = apply_deterministic_pad_labels(combined, save_bins=True)
        combined.to_csv(out_path, index=False)
        return out_path

    raw = _read_tabular(user_path)
    raw = standardize_dataset_columns(raw)
    raw = _coerce_timestamp(raw)
    raw = ensure_demographic_columns(raw)
    combined = pd.concat([syn_u, raw], ignore_index=True)
    combined.to_csv(out_path, index=False)

    from .label_rules import apply_deterministic_pad_labels

    combined = pd.read_csv(out_path)
    combined = apply_deterministic_pad_labels(combined, save_bins=True)
    combined.to_csv(out_path, index=False)
    return out_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Merge vest CSV with stratified 33–38 °C synthetic rows for training."
    )
    parser.add_argument(
        "--user",
        default=os.path.join(config.BASE_DIR, "vest_training_combined.csv"),
        help="Input CSV path",
    )
    parser.add_argument(
        "--out",
        default=os.path.join(config.BASE_DIR, "vest_training_combined_expanded.csv"),
        help="Output combined CSV",
    )
    parser.add_argument("--n", type=int, default=24_000, help="Number of synthetic rows")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    out = merge_user_with_temperature_synthetic(args.user, args.out, n_synthetic=args.n, seed=args.seed)
    print("Wrote:", os.path.abspath(out))


if __name__ == "__main__":
    main()
