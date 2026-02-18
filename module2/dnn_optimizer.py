"""
Phase 3 — DNN heating optimization (decision brain).
Inputs: current_temp, predicted_temp, motion, pulse -> Outputs: pad1, pad2 (sigmoid * 100 = PWM %).
"""
import os
import numpy as np
from tensorflow import keras
from tensorflow.keras import layers

from . import config

def build_dnn(input_dim=4):
    model = keras.Sequential([
        layers.Input(shape=(input_dim,)),
        layers.Dense(config.DNN_HIDDEN[0], activation="relu"),
        layers.Dense(config.DNN_HIDDEN[1], activation="relu"),
        layers.Dense(config.DNN_OUTPUT_DIM, activation="sigmoid"),
    ])
    model.compile(optimizer="adam", loss="mse", metrics=["mae"])
    return model

def prepare_dnn_data():
    X_scaled = np.load(os.path.join(config.DATA_DIR, "X_scaled.npy"))
    n = len(X_scaled) - 1
    X_dnn = np.zeros((n, 4))
    X_dnn[:, 0] = X_scaled[:-1, 0]
    X_dnn[:, 1] = X_scaled[1:, 0]
    X_dnn[:, 2] = X_scaled[:-1, 2]
    X_dnn[:, 3] = X_scaled[:-1, 1]
    y_dnn = X_scaled[:-1, 3:5]
    return X_dnn, y_dnn

def train_dnn(X_dnn, y_dnn):
    model = build_dnn(input_dim=X_dnn.shape[1])
    model.fit(
        X_dnn, y_dnn,
        epochs=config.EPOCHS,
        batch_size=config.BATCH_SIZE,
        validation_split=config.VALIDATION_SPLIT,
        verbose=1,
    )
    model.save(config.DNN_MODEL_PATH)
    print("Saved DNN to", config.DNN_MODEL_PATH)
    return model

def predict_pwm(model, current_temp_norm, predicted_temp_norm, motion_norm, pulse_norm):
    x = np.array([[current_temp_norm, predicted_temp_norm, motion_norm, pulse_norm]], dtype=np.float32)
    out = model.predict(x, verbose=0)
    pwm1 = float(out[0, 0] * config.PWM_MAX)
    pwm2 = float(out[0, 1] * config.PWM_MAX)
    return pwm1, pwm2

def run():
    X_dnn, y_dnn = prepare_dnn_data()
    return train_dnn(X_dnn, y_dnn)
