"""
Phase 2 — Conv1D sequence classifier for pad_level (4 classes).

TensorFlow Lite–friendly: no LSTM/RNN (no TensorList). Input (batch, SEQ_LENGTH, FEATURE_DIM_SEQ).

Loss: SparseCategoricalCrossentropy with label smoothing. Class weights: balanced.
"""
from __future__ import annotations

import os
from typing import Dict, Optional

import numpy as np
import tensorflow as tf
from sklearn.metrics import (
    balanced_accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
)
from sklearn.model_selection import train_test_split
from sklearn.utils.class_weight import compute_class_weight
from tensorflow import keras
from tensorflow.keras.layers import Conv1D, Dense, Dropout, Flatten
from tensorflow.keras.models import Sequential

from . import config

# Smaller head + stronger dropout to reduce overconfidence
CLASSIFIER_DENSE_UNITS = 32
CLASSIFIER_DROPOUT = 0.3
LABEL_SMOOTHING = 0.1


def _split_stratified_holdout(
    X: np.ndarray, y: np.ndarray, test_ratio: float = 0.15, val_ratio: float = 0.15
):
    """Stratified 70/15/15 (data are already class-balanced IID)."""
    seed = config.SHUFFLE_SEED
    X_tr, X_te, y_tr, y_te = train_test_split(
        X, y, test_size=test_ratio, random_state=seed, stratify=y
    )
    val_size = val_ratio / (1.0 - test_ratio)
    X_train, X_val, y_train, y_val = train_test_split(
        X_tr, y_tr, test_size=val_size, random_state=seed, stratify=y_tr
    )
    return X_train, y_train, X_val, y_val, X_te, y_te


def _balanced_class_weight_dict(y: np.ndarray) -> Dict[int, float]:
    """sklearn 'balanced' weights for integer labels 0..NUM_PAD_CLASSES-1."""
    y = np.asarray(y).astype(np.int64).reshape(-1)
    classes = np.arange(config.NUM_PAD_CLASSES)
    weights = compute_class_weight(class_weight="balanced", classes=classes, y=y)
    return {int(i): float(weights[i]) for i in range(config.NUM_PAD_CLASSES)}


def build_pad_classifier(
    seq_length: Optional[int] = None,
    feature_dim: Optional[int] = None,
    num_classes: Optional[int] = None,
) -> keras.Model:
    seq_length = int(seq_length or config.SEQ_LENGTH)
    feature_dim = int(feature_dim or config.FEATURE_DIM_SEQ)
    num_classes = int(num_classes or config.NUM_PAD_CLASSES)

    model = Sequential(
        [
            Conv1D(
                32,
                kernel_size=3,
                activation="relu",
                input_shape=(seq_length, feature_dim),
            ),
            Conv1D(16, kernel_size=3, activation="relu"),
            Flatten(),
            Dense(CLASSIFIER_DENSE_UNITS, activation="relu"),
            Dropout(CLASSIFIER_DROPOUT),
            Dense(num_classes, activation="softmax", dtype="float32"),
        ]
    )
    loss = keras.losses.SparseCategoricalCrossentropy()
    model.compile(
        optimizer="adam",
        loss=loss,
        metrics=["accuracy"],
    )
    return model


def _print_label_distribution(name: str, y: np.ndarray) -> None:
    y = np.asarray(y).astype(np.int64).reshape(-1)
    n = max(len(y), 1)
    print("%s (n=%s):" % (name, len(y)))
    for i, cname in enumerate(config.PAD_LEVEL_CLASSES):
        k = int(np.sum(y == i))
        print("  %s: %s (%.2f%%)" % (cname, k, 100.0 * k / n))


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

    print("\n=== Class distribution (full sequence set, before train/val/test split) ===")
    _print_label_distribution("All", y)

    X_train, y_train, X_val, y_val, X_test, y_test = _split_stratified_holdout(X, y)

    print("\n=== Class distribution (splits) ===")
    _print_label_distribution("Train", y_train)
    _print_label_distribution("Val", y_val)
    _print_label_distribution("Test", y_test)

    class_weight = _balanced_class_weight_dict(y_train)
    print("\nclass_weight (balanced on train):", class_weight)

    model = build_pad_classifier(seq_len, n_features, num_classes)
    callbacks = [
        keras.callbacks.EarlyStopping(
            monitor="val_loss",
            mode="min",
            patience=18,
            restore_best_weights=True,
            min_delta=1e-5,
        ),
        keras.callbacks.ReduceLROnPlateau(
            monitor="val_loss",
            factor=0.5,
            patience=5,
            min_lr=1e-6,
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
        class_weight=class_weight,
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
        f.write(
            "Pad level classifier (Conv1D, sparse CE + label smoothing, balanced class_weight) — test set\n"
        )
        f.write(
            "seq_len=%d n_features=%d num_classes=%d dense=%s dropout=%s label_smoothing=%s\n"
            % (
                seq_len,
                n_features,
                num_classes,
                CLASSIFIER_DENSE_UNITS,
                CLASSIFIER_DROPOUT,
                LABEL_SMOOTHING,
            )
        )
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
    """row_scaled_seq_features: (1, FEATURE_DIM_SEQ) after StandardScaler — tiled to sequence."""
    r = np.asarray(row_scaled_seq_features, dtype=np.float32).reshape(1, -1)
    seq = np.tile(r, (1, config.SEQ_LENGTH, 1))
    return model.predict(seq, verbose=0)[0]
