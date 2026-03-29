"""
Phase 2 — LSTM temperature prediction.
Build, train, evaluate; save model. Input: (samples, 20, features) -> next_temperature.
"""
import os
import pickle
import numpy as np
import matplotlib.pyplot as plt
from sklearn.metrics import classification_report
from tensorflow import keras
from tensorflow.keras import layers

from . import config

def _split_time_series(X, y, train_ratio=0.7, val_ratio=0.15):
    n = len(X)
    i_train = int(n * train_ratio)
    i_val = int(n * (train_ratio + val_ratio))
    X_train, y_train = X[:i_train], y[:i_train]
    X_val, y_val = X[i_train:i_val], y[i_train:i_val]
    X_test, y_test = X[i_val:], y[i_val:]
    return X_train, y_train, X_val, y_val, X_test, y_test

def build_lstm(seq_length=None, n_features=None):
    seq_length = seq_length or config.SEQ_LENGTH
    n_features = n_features or len(config.FEATURE_COLS)
    reg = keras.regularizers.l2(5e-5)
    model = keras.Sequential([
        layers.Input(shape=(seq_length, n_features)),
        layers.LSTM(
            config.LSTM_UNITS,
            return_sequences=True,
            kernel_regularizer=reg,
            recurrent_regularizer=reg,
        ),
        layers.Dropout(config.LSTM_DROPOUT),
        layers.LSTM(
            config.LSTM_UNITS_2,
            kernel_regularizer=reg,
            recurrent_regularizer=reg,
        ),
        layers.Dropout(config.LSTM_DROPOUT + 0.05),
        layers.Dense(config.DENSE_UNITS, activation="relu", kernel_regularizer=reg),
        layers.Dense(1),
    ])
    model.compile(
        optimizer=keras.optimizers.Adam(learning_rate=8e-4),
        loss=keras.losses.Huber(delta=0.06),
        metrics=["mae"],
    )
    return model

def train_lstm(X_seq, y_seq):
    keras.backend.clear_session()
    X_train, y_train, X_val, y_val, X_test, y_test = _split_time_series(X_seq, y_seq)
    model = build_lstm(seq_length=X_seq.shape[1], n_features=X_seq.shape[2])
    callbacks = [
        keras.callbacks.EarlyStopping(
            monitor="val_loss",
            patience=12,
            restore_best_weights=True,
            min_delta=1e-5,
        ),
        keras.callbacks.ReduceLROnPlateau(
            monitor="val_loss",
            factor=0.5,
            patience=3,
            min_lr=1e-7,
            verbose=1,
        ),
    ]
    model.fit(
        X_train, y_train,
        epochs=config.EPOCHS_LSTM,
        batch_size=config.BATCH_SIZE,
        validation_data=(X_val, y_val),
        callbacks=callbacks,
        verbose=1,
    )
    model.save(config.LSTM_MODEL_PATH)
    print("Saved LSTM to", config.LSTM_MODEL_PATH)
    return model, (X_test, y_test)

def _temp_class(temp_c):
    if temp_c < config.TEMP_COMFORT_LOW_C:
        return "cold"
    if temp_c <= config.TEMP_COMFORT_HIGH_C:
        return "comfort"
    return "hot"

def evaluate_lstm(model, X_seq, y_seq, scaler_y):
    """Plot predicted vs real, compute RMSE."""
    pred_scaled = model.predict(X_seq, verbose=0)
    pred = scaler_y.inverse_transform(pred_scaled)
    real = scaler_y.inverse_transform(y_seq.reshape(-1, 1))
    rmse = np.sqrt(np.mean((pred - real) ** 2))
    print("Test RMSE (°C):", rmse)

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

    # Classification view of temperature prediction quality.
    y_true_cls = np.array([_temp_class(v) for v in real.reshape(-1)])
    y_pred_cls = np.array([_temp_class(v) for v in pred.reshape(-1)])
    class_labels = ["cold", "comfort", "hot"]
    cls_report = classification_report(
        y_true_cls,
        y_pred_cls,
        labels=class_labels,
        zero_division=0,
    )
    report_path = os.path.join(config.DATA_DIR, "lstm_classification_report.txt")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("LSTM temperature class report (cold/comfort/hot)\n")
        f.write("Classes based on comfort thresholds in config.py.\n\n")
        f.write(cls_report)
    print("\nLSTM classification report:\n", cls_report)
    print("Saved:", report_path)
    return rmse

def run():
    """Load prepared data, train and evaluate LSTM."""
    X_seq = np.load(os.path.join(config.DATA_DIR, "X_seq.npy"))
    y_seq = np.load(os.path.join(config.DATA_DIR, "y_seq.npy"))
    with open(config.SCALER_TARGET_PATH, "rb") as f:
        scaler_y = pickle.load(f)

    model, (X_test, y_test) = train_lstm(X_seq, y_seq)
    evaluate_lstm(model, X_test, y_test, scaler_y)
    return model
