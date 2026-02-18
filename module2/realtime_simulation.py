"""
Phase 6 — Real-time simulation.
Read dataset row by row, treat as live data, run AI pipeline, print output.
Proves the cloud pipeline works before connecting hardware.
"""
import os
import pickle
import numpy as np
import pandas as pd

from . import config
from . import safety

def run_simulation(max_steps=200, verbose=True):
    """
    Loop: read dataset row → act as live data → LSTM predict → DNN optimize → safety → print.
    """
    from tensorflow import keras

    df = pd.read_csv(config.DATASET_PATH)
    lstm = keras.models.load_model(config.LSTM_MODEL_PATH)
    dnn = keras.models.load_model(config.DNN_MODEL_PATH)
    with open(config.SCALER_FEATURES_PATH, "rb") as f:
        scaler_X = pickle.load(f)
    with open(config.SCALER_TARGET_PATH, "rb") as f:
        scaler_y = pickle.load(f)

    X_scaled = scaler_X.transform(df[config.FEATURE_COLS].values)
    max_steps = min(max_steps, len(df) - config.SEQ_LENGTH - 1)

    print("Real-time simulation: dataset row → predict → optimize → safety → command")
    print("-" * 70)

    for i in range(config.SEQ_LENGTH, config.SEQ_LENGTH + max_steps):
        row = df.iloc[i]
        temp = row[config.COL_TEMP]
        pulse = row[config.COL_PULSE]
        motion = row[config.COL_MOTION]
        pad1 = row[config.COL_PAD1]
        pad2 = row[config.COL_PAD2]

        seq = X_scaled[i - config.SEQ_LENGTH : i]
        X_seq = np.array([seq], dtype=np.float32)
        pred_scaled = lstm.predict(X_seq, verbose=0)
        pred_temp_norm = float(pred_scaled[0, 0])
        row_scaled = X_scaled[i]
        current_temp_norm, pulse_norm = row_scaled[0], row_scaled[1]
        motion_norm = row_scaled[2]

        dnn_in = np.array([[current_temp_norm, pred_temp_norm, motion_norm, pulse_norm]], dtype=np.float32)
        dnn_out = dnn.predict(dnn_in, verbose=0)
        pwm1 = float(dnn_out[0, 0] * config.PWM_MAX)
        pwm2 = float(dnn_out[0, 1] * config.PWM_MAX)

        pwm1, pwm2 = safety.apply_safety_overrides(temp, pulse, pwm1, pwm2, sensor_temp_ok=True, sensor_pulse_ok=True)

        if verbose:
            print(f"Step {i - config.SEQ_LENGTH + 1}: T={temp:.2f} P={pulse} M={motion:.2f} "
                  f"→ pred_T_norm={pred_temp_norm:.3f} → CMD pad1={pwm1:.1f}% pad2={pwm2:.1f}%")

    print("-" * 70)
    print("Simulation done. Cloud pipeline: Read → Predict → Optimize → Safety → Command.")
