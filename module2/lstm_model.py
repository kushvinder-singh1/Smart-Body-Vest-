"""
Phase 2 — LSTM temperature prediction.
Build, train, evaluate; save model. Input: (samples, 20, features) -> next_temperature.
"""
import os
import pickle
import numpy as np
import matplotlib.pyplot as plt
from tensorflow import keras
from tensorflow.keras import layers

from . import config

def build_lstm(seq_length=None, n_features=None):
    seq_length = seq_length or config.SEQ_LENGTH
    n_features = n_features or len(config.FEATURE_COLS)
    model = keras.Sequential([
        layers.Input(shape=(seq_length, n_features)),
        layers.LSTM(config.LSTM_UNITS),
        layers.Dropout(config.LSTM_DROPOUT),
        layers.Dense(config.DENSE_UNITS, activation="relu"),
        layers.Dense(1),
    ])
    model.compile(optimizer="adam", loss="mse", metrics=["mae"])
    return model

def train_lstm(X_seq, y_seq):
    model = build_lstm(seq_length=X_seq.shape[1], n_features=X_seq.shape[2])
    model.fit(
        X_seq, y_seq,
        epochs=config.EPOCHS,
        batch_size=config.BATCH_SIZE,
        validation_split=config.VALIDATION_SPLIT,
        verbose=1,
    )
    model.save(config.LSTM_MODEL_PATH)
    print("Saved LSTM to", config.LSTM_MODEL_PATH)
    return model

def evaluate_lstm(model, X_seq, y_seq, scaler_y):
    """Plot predicted vs real, compute RMSE."""
    pred_scaled = model.predict(X_seq, verbose=0)
    pred = scaler_y.inverse_transform(pred_scaled)
    real = scaler_y.inverse_transform(y_seq.reshape(-1, 1))
    rmse = np.sqrt(np.mean((pred - real) ** 2))
    print("RMSE (°C):", rmse)

    fig, ax = plt.subplots(figsize=(10, 5))
    n_show = min(500, len(real))
    ax.plot(real[:n_show], label="Real", alpha=0.8)
    ax.plot(pred[:n_show], label="Predicted", alpha=0.8)
    ax.set_xlabel("Sample")
    ax.set_ylabel("Temperature (°C)")
    ax.set_title(f"LSTM: Predicted vs real temperature (RMSE = {rmse:.4f} °C)")
    ax.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(config.PLOTS_DIR, "04_lstm_predicted_vs_real.png"), dpi=120)
    plt.close()
    print("Saved: 04_lstm_predicted_vs_real.png")
    return rmse

def run():
    """Load prepared data, train and evaluate LSTM."""
    X_seq = np.load(os.path.join(config.DATA_DIR, "X_seq.npy"))
    y_seq = np.load(os.path.join(config.DATA_DIR, "y_seq.npy"))
    with open(config.SCALER_TARGET_PATH, "rb") as f:
        scaler_y = pickle.load(f)

    model = train_lstm(X_seq, y_seq)
    evaluate_lstm(model, X_seq, y_seq, scaler_y)
    return model
