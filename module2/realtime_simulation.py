"""
Phase 6 — Real-time simulation (time-series aligned with training).

Uses rows ordered by (session_id, timestamp), per-step Δtemp/Δpulse, then sliding windows
over MinMax-scaled FEATURE_COLS_SEQ (10-D).
"""
import pickle

import numpy as np

from . import config
from . import safety
from .data_prep import add_session_time_derivatives, enforce_time_series_order, read_dataset_file


def run_simulation(max_steps=200, verbose=True):
    from .keras_load import load_keras_model_for_inference

    df = read_dataset_file(sync_labels_from_rules=True)
    df = enforce_time_series_order(df)
    df = add_session_time_derivatives(df)

    clf = load_keras_model_for_inference(config.CLASSIFIER_MODEL_PATH)
    with open(config.SCALER_FEATURES_PATH, "rb") as f:
        scaler_X = pickle.load(f)

    X = df[config.FEATURE_COLS_SEQ].values.astype(np.float32)
    X_scaled = scaler_X.transform(X)
    max_steps = min(max_steps, len(df))

    print("Real-time simulation (time-series windows) → pad_level → PWM → safety")
    print("-" * 70)

    sl = config.SEQ_LENGTH

    def _window_at(i):
        start = max(0, i - sl + 1)
        win = X_scaled[start : i + 1]
        if win.shape[0] < sl:
            pad = np.tile(win[0:1], (sl - win.shape[0], 1))
            win = np.vstack([pad, win])
        else:
            win = win[-sl:]
        return win.reshape(1, sl, -1)

    for i in range(max_steps):
        row = df.iloc[i]
        temp = float(row[config.COL_TEMP])
        pulse = float(row[config.COL_PULSE])
        motion = float(row[config.COL_MOTION])
        true_level = str(row[config.COL_PAD_LEVEL]).upper().strip()

        probs = clf.predict(_window_at(i), verbose=0)[0]
        k = int(np.argmax(probs))
        pred_name = config.PAD_LEVEL_CLASSES[k]
        pwm1, pwm2 = config.PAD_CLASS_INDEX_TO_PWM[k]
        pwm1, pwm2 = safety.apply_safety_overrides(
            temp, pulse, pwm1, pwm2, sensor_temp_ok=True, sensor_pulse_ok=True
        )

        if verbose:
            print(
                f"Step {i + 1}: T={temp:.2f} P={pulse:.0f} M={motion:.0f} "
                f"true={true_level} pred={pred_name} -> pad1={pwm1:.1f}% pad2={pwm2:.1f}%"
            )

    print("-" * 70)
    print("Simulation done.")
