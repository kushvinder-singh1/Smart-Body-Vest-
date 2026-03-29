"""
Synthetic vest sessions: canonical columns only (no pad PWM, no raw motion_level).
"""
import os
import numpy as np
import pandas as pd

from . import config

_PAD_LABEL_TO_PWM = {
    "OFF": (0.0, 0.0),
    "LOW": (25.0, 25.0),
    "MEDIUM": (50.0, 50.0),
    "HIGH": (85.0, 85.0),
}


def _pick_pad_level_placeholder() -> str:
    """Placeholder only — ``merge_user_and_synthetic`` + training apply deterministic labels."""
    return "MEDIUM"


def generate_synthetic_dataframe(
    n_sessions: int = 96,
    steps_per_session: int = 320,
    seed: int = 42,
) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows = []
    global_ts = 0
    for s in range(n_sessions):
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
            p1, p2 = _PAD_LABEL_TO_PWM[pad_label]
            pwm_avg = 0.5 * (p1 + p2)

            heating = 0.028 * (pwm_avg / 100.0) * (9.0 + 0.05 * (70.0 - age / 78.0 * 20.0))
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
                    "session_id": s,
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
    from .data_prep import ensure_demographic_columns, finalize_training_dataframe, load_and_clean_file

    syn = generate_synthetic_dataframe(
        n_sessions=n_sessions, steps_per_session=steps_per_session, seed=seed
    )
    syn_u = ensure_demographic_columns(syn)
    syn_u = finalize_training_dataframe(syn_u)

    if not os.path.isfile(user_path):
        syn_u.to_csv(out_path, index=False)
        from .label_rules import apply_deterministic_pad_labels

        combined = pd.read_csv(out_path)
        combined = apply_deterministic_pad_labels(combined, save_bins=True)
        combined.to_csv(out_path, index=False)
        return out_path

    raw = load_and_clean_file(user_path)
    max_sid = int(syn_u["session_id"].max()) + 1
    raw = raw.copy()
    raw["session_id"] = max_sid
    combined = pd.concat([syn_u, raw], ignore_index=True)
    combined.to_csv(out_path, index=False)

    from .label_rules import apply_deterministic_pad_labels

    combined = pd.read_csv(out_path)
    combined = apply_deterministic_pad_labels(combined, save_bins=True)
    combined.to_csv(out_path, index=False)
    return out_path
