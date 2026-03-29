"""
Phase 2 — Time-series LSTM + DNN classifier for pad_level (4 classes).

Graph: Input (batch, timesteps, features) → BiLSTM → LSTM → concat(last timestep) →
Dense head (DNN). All tensors connect to the final softmax; no unused branches.

Loss: sparse focal (hard examples + adjacent-class mistakes). Scaling: StandardScaler
from data_prep (re-run Phase 1 after changing scaler).
"""
import os

import numpy as np
import tensorflow as tf
from sklearn.metrics import (
    balanced_accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
)
from sklearn.model_selection import train_test_split
from tensorflow import keras
from tensorflow.keras import layers

from . import config


def _sparse_categorical_focal_loss(gamma: float = 2.0):
    """
    Focal loss for sparse integer labels. Slightly higher alpha on LOW/MEDIUM/HIGH
    to sharpen boundaries between adjacent ordered classes.
    """
    n = config.NUM_PAD_CLASSES
    alpha = tf.constant([0.35, 0.55, 0.55, 0.45], dtype=tf.float32)

    def loss(y_true, y_pred):
        y_true = tf.cast(tf.reshape(y_true, [-1]), tf.int32)
        y_pred = tf.clip_by_value(y_pred, 1e-7, 1.0 - 1e-7)
        one_hot = tf.one_hot(y_true, depth=n, dtype=tf.float32)
        p_t = tf.reduce_sum(one_hot * y_pred, axis=-1)
        ce = -tf.reduce_sum(one_hot * tf.math.log(y_pred), axis=-1)
        mod = tf.pow(1.0 - p_t, gamma)
        a = tf.gather(alpha, y_true)
        return tf.reduce_mean(a * mod * ce)

    return loss


def _build_model(seq_len: int, n_features: int, num_classes: int) -> keras.Model:
    """
    LSTM encodes the sequence; last-frame skip connects raw per-timestep features into
    the DNN head so static + dynamic information both affect logits.
    """
    reg = keras.regularizers.l2(2e-5)
    inp = layers.Input(shape=(seq_len, n_features), name="seq_features")

    x = layers.Bidirectional(
        layers.LSTM(
            88,
            return_sequences=True,
            kernel_regularizer=reg,
            recurrent_regularizer=reg,
        ),
        name="bilstm_1",
    )(inp)
    x = layers.Dropout(0.22)(x)
    x = layers.LSTM(
        64,
        return_sequences=False,
        kernel_regularizer=reg,
        recurrent_regularizer=reg,
        name="lstm_2",
    )(x)
    x = layers.Dropout(0.2)(x)

    last = layers.Lambda(lambda t: t[:, -1, :], name="last_timestep")(inp)
    x = layers.Concatenate(name="lstm_plus_last")([x, last])

    x = layers.Dense(144, activation="elu", kernel_regularizer=reg, name="dense_1")(x)
    x = layers.BatchNormalization(name="bn_1")(x)
    x = layers.Dropout(0.32)(x)
    x = layers.Dense(72, activation="elu", kernel_regularizer=reg, name="dense_2")(x)
    x = layers.Dropout(0.18)(x)
    out = layers.Dense(num_classes, activation="softmax", dtype="float32", name="pad_level")(x)

    model = keras.Model(inputs=inp, outputs=out, name="lstm_dnn_pad_classifier")
    try:
        opt = keras.optimizers.AdamW(learning_rate=3e-4, weight_decay=1e-4)
    except Exception:
        opt = keras.optimizers.Adam(learning_rate=3e-4)
    model.compile(
        optimizer=opt,
        loss=_sparse_categorical_focal_loss(gamma=2.0),
        metrics=["sparse_categorical_accuracy"],
    )
    return model


def run():
    keras.backend.clear_session()
    X = np.load(os.path.join(config.DATA_DIR, "X_seq_pad.npy"))
    y = np.load(os.path.join(config.DATA_DIR, "y_pad_class_seq.npy"))

    num_classes = config.NUM_PAD_CLASSES
    n_features = X.shape[2]
    seq_len = X.shape[1]
    assert n_features == config.FEATURE_DIM_SEQ, (
        "Expected %d sequence features, got %d — re-run data_prep.run()"
        % (config.FEATURE_DIM_SEQ, n_features)
    )
    assert num_classes == 4

    X_train, X_temp, y_train, y_temp = train_test_split(
        X,
        y,
        test_size=0.3,
        random_state=config.SHUFFLE_SEED,
        stratify=y,
    )
    X_val, X_test, y_val, y_test = train_test_split(
        X_temp,
        y_temp,
        test_size=0.5,
        random_state=config.SHUFFLE_SEED,
        stratify=y_temp,
    )

    model = _build_model(seq_len, n_features, num_classes)
    callbacks = [
        keras.callbacks.EarlyStopping(
            monitor="val_loss",
            mode="min",
            patience=22,
            restore_best_weights=True,
            min_delta=1e-5,
        ),
        keras.callbacks.ReduceLROnPlateau(
            monitor="val_loss",
            factor=0.45,
            patience=6,
            min_lr=5e-7,
            verbose=1,
        ),
    ]
    model.fit(
        X_train,
        y_train,
        epochs=config.EPOCHS_CLASSIFIER,
        batch_size=config.BATCH_SIZE_CLASSIFIER,
        validation_data=(X_val, y_val),
        callbacks=callbacks,
        verbose=1,
    )

    model.save(config.CLASSIFIER_MODEL_PATH)
    print("Saved classifier to", config.CLASSIFIER_MODEL_PATH)

    y_pred = np.argmax(model.predict(X_test, verbose=0), axis=1)
    labels = list(config.PAD_LEVEL_CLASSES)

    acc = float(np.mean(y_pred == y_test))
    bacc = float(balanced_accuracy_score(y_test, y_pred))
    macro_f1 = float(f1_score(y_test, y_pred, average="macro", zero_division=0))
    weighted_f1 = float(f1_score(y_test, y_pred, average="weighted", zero_division=0))

    report = classification_report(
        y_test,
        y_pred,
        labels=list(range(len(labels))),
        target_names=labels,
        zero_division=0,
    )
    cm = confusion_matrix(y_test, y_pred, labels=list(range(4)))

    print("\nTest accuracy: {:.4f}".format(acc))
    print("Balanced accuracy: {:.4f}".format(bacc))
    print("Macro F1: {:.4f} | Weighted F1: {:.4f}".format(macro_f1, weighted_f1))
    print("\nConfusion matrix (rows=true, cols=pred):")
    print(cm)
    print("\n", report)

    path = os.path.join(config.DATA_DIR, "pad_classifier_report.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write("Pad level classifier (LSTM + DNN, focal loss) — hold-out test set\n")
        f.write("seq_len=%d n_features=%d num_classes=%d\n" % (seq_len, n_features, num_classes))
        f.write(f"Accuracy: {acc:.4f}\n")
        f.write(f"Balanced accuracy: {bacc:.4f}\n")
        f.write(f"Macro F1: {macro_f1:.4f} | Weighted F1: {weighted_f1:.4f}\n\n")
        f.write("Confusion matrix [true x pred]:\n")
        f.write(np.array2string(cm))
        f.write("\n\n")
        f.write(report)
    print("Saved:", path)
    return model


def predict_pad_class_proba(row_scaled_seq_features, model):
    """row_scaled_seq_features: (1, FEATURE_DIM_SEQ) after StandardScaler."""
    r = np.asarray(row_scaled_seq_features, dtype=np.float32).reshape(1, -1)
    seq = np.tile(r, (1, config.SEQ_LENGTH, 1))
    return model.predict(seq, verbose=0)[0]
