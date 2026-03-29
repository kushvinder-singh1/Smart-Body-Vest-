"""
Phase 3 — DNN heating optimization (decision brain).
Inputs: current_temp, predicted_temp, motion, pulse, age, height, weight, gender
-> Outputs: pad1, pad2 (sigmoid * 100 = PWM %).
"""
import os
import numpy as np
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

def build_dnn(input_dim=config.DNN_INPUT_DIM):
    reg = keras.regularizers.l2(5e-5)
    model = keras.Sequential([
        layers.Input(shape=(input_dim,)),
        layers.Dense(config.DNN_HIDDEN[0], activation="relu", kernel_regularizer=reg),
        layers.Dropout(0.15),
        layers.Dense(config.DNN_HIDDEN[1], activation="relu", kernel_regularizer=reg),
        layers.Dropout(0.08),
        layers.Dense(config.DNN_OUTPUT_DIM, activation="sigmoid"),
    ])
    model.compile(
        optimizer=keras.optimizers.Adam(learning_rate=8e-4),
        loss=keras.losses.Huber(delta=0.04),
        metrics=["mae"],
    )
    return model


def prepare_dnn_data():
    """
    Build DNN inputs to match firebase / realtime inference: column 1 must be LSTM
    predicted temperature (scaled), not the one-step-ahead *actual* temp.
    """
    keras.backend.clear_session()
    from .keras_load import load_keras_model_for_inference

    lstm = load_keras_model_for_inference(config.LSTM_MODEL_PATH)
    X_scaled = np.load(os.path.join(config.DATA_DIR, "X_scaled.npy"))

    n = len(X_scaled) - 1
    idx = config.FEATURE_INDEX
    idx_temp = idx[config.COL_TEMP]
    sl = config.SEQ_LENGTH

    X_dnn = np.zeros((n, config.DNN_INPUT_DIM), dtype=np.float32)
    X_dnn[:, 0] = X_scaled[:-1, idx_temp]
    # LSTM preds from sliding windows on X_scaled (matches realtime_simulation; robust when
    # X_seq.npy was built with session filtering and has a different row count than n - sl).
    pred_lstm = np.zeros(n, dtype=np.float32)
    pred_lstm[:sl] = X_scaled[:sl, idx_temp]
    chunk = 2048
    starts = np.arange(sl, n, dtype=np.int32)
    for i in range(0, len(starts), chunk):
        s = starts[i : i + chunk]
        win = np.stack([X_scaled[int(j) - sl : int(j)] for j in s], axis=0)
        pred_lstm[s] = lstm.predict(win, verbose=0, batch_size=256)[:, 0]
    X_dnn[:, 1] = pred_lstm
    X_dnn[:, 2] = X_scaled[:-1, idx[config.COL_MOTION]]
    X_dnn[:, 3] = X_scaled[:-1, idx[config.COL_PULSE]]
    X_dnn[:, 4] = X_scaled[:-1, idx[config.COL_AGE]]
    X_dnn[:, 5] = X_scaled[:-1, idx[config.COL_HEIGHT_CM]]
    X_dnn[:, 6] = X_scaled[:-1, idx[config.COL_WEIGHT_KG]]
    X_dnn[:, 7] = X_scaled[:-1, idx[config.COL_GENDER]]
    y_path = os.path.join(config.DATA_DIR, "y_dnn_pads_phys.npy")
    if os.path.isfile(y_path):
        y_dnn = np.load(y_path)
    else:
        y_dnn = X_scaled[:-1, idx[config.COL_PAD1] : idx[config.COL_PAD2] + 1]

    del lstm
    keras.backend.clear_session()
    print(
        "DNN inputs aligned with LSTM: pred_temp column = LSTM output "
        f"(not actual t+1). Sample rows: {n}"
    )
    return X_dnn, y_dnn

def train_dnn(X_dnn, y_dnn):
    keras.backend.clear_session()
    X_train, y_train, X_val, y_val, X_test, y_test = _split_time_series(X_dnn, y_dnn)
    model = build_dnn(input_dim=X_dnn.shape[1])
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
        epochs=config.EPOCHS_DNN,
        batch_size=config.BATCH_SIZE,
        validation_data=(X_val, y_val),
        callbacks=callbacks,
        shuffle=True,
        verbose=1,
    )
    model.save(config.DNN_MODEL_PATH)
    print("Saved DNN to", config.DNN_MODEL_PATH)
    return model, (X_test, y_test)

def _pwm_class_from_norm(v_norm):
    """v_norm is 0–1 fraction of PWM; map to labels for reporting."""
    v = float(v_norm) * config.PWM_MAX
    if v < 12.5:
        return "off"
    if v < 37.5:
        return "low"
    if v < 67.5:
        return "med"
    return "high"

def evaluate_dnn(model, X_dnn, y_dnn):
    pred = model.predict(X_dnn, verbose=0)

    mae_norm = np.mean(np.abs(pred - y_dnn), axis=0)
    mae_pct = mae_norm * config.PWM_MAX
    print(
        "DNN test MAE (approx % PWM): pad1={:.2f}% pad2={:.2f}%".format(mae_pct[0], mae_pct[1])
    )

    y1_true = np.array([_pwm_class_from_norm(v) for v in y_dnn[:, 0]])
    y1_pred = np.array([_pwm_class_from_norm(v) for v in pred[:, 0]])
    y2_true = np.array([_pwm_class_from_norm(v) for v in y_dnn[:, 1]])
    y2_pred = np.array([_pwm_class_from_norm(v) for v in pred[:, 1]])
    labels = ["off", "low", "med", "high"]

    report_pad1 = classification_report(y1_true, y1_pred, labels=labels, zero_division=0)
    report_pad2 = classification_report(y2_true, y2_pred, labels=labels, zero_division=0)

    report_path = os.path.join(config.DATA_DIR, "dnn_classification_report.txt")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("DNN heating class report (pad PWM classes)\n")
        f.write("Bins: off <12.5%, low 12.5-37.5, med 37.5-67.5, high >67.5 (matches 0/25/50/85).\n")
        f.write(
            f"Test MAE (approx % PWM): pad1={mae_pct[0]:.2f}% pad2={mae_pct[1]:.2f}%\n\n"
        )
        f.write("Pad1 classification report\n")
        f.write(report_pad1)
        f.write("\nPad2 classification report\n")
        f.write(report_pad2)

    print("\nDNN classification report (Pad1):\n", report_pad1)
    print("DNN classification report (Pad2):\n", report_pad2)
    print("Saved:", report_path)

def predict_pwm(
    model,
    current_temp_norm,
    predicted_temp_norm,
    motion_norm,
    pulse_norm,
    age_norm,
    height_norm,
    weight_norm,
    gender_norm,
):
    x = np.array(
        [[
            current_temp_norm,
            predicted_temp_norm,
            motion_norm,
            pulse_norm,
            age_norm,
            height_norm,
            weight_norm,
            gender_norm,
        ]],
        dtype=np.float32,
    )
    out = model.predict(x, verbose=0)
    pwm1 = float(out[0, 0] * config.PWM_MAX)
    pwm2 = float(out[0, 1] * config.PWM_MAX)
    return pwm1, pwm2

def run():
    X_dnn, y_dnn = prepare_dnn_data()
    model, (X_test, y_test) = train_dnn(X_dnn, y_dnn)
    evaluate_dnn(model, X_test, y_test)
    return model
