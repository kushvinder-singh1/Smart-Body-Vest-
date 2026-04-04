#!/usr/bin/env python3
"""
Convert trained Keras pad_level classifier to TensorFlow Lite (float, default optimizations).

Uses TFLite BUILTINS only (no SELECT_TF_OPS) — compatible with Conv1D + Dense graphs.

Usage (from Smart-Body-Vest- project root):
  python tflite_convert.py
  python tflite_convert.py --keras path/to/model.keras --out path/to/out.tflite

Requires: tensorflow
"""
from __future__ import annotations

import argparse
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")


def main() -> None:
    parser = argparse.ArgumentParser(description="Keras → TFLite for pad_level classifier")
    parser.add_argument(
        "--keras",
        default=None,
        help="Input .keras/.h5 path (default: module2 config CLASSIFIER_MODEL_PATH)",
    )
    parser.add_argument(
        "--out",
        default=None,
        help="Output .tflite path (default: module2 config TFLITE_MODEL_PATH)",
    )
    args = parser.parse_args()

    from module2 import config

    keras_path = os.path.abspath(args.keras or config.CLASSIFIER_MODEL_PATH)
    out_path = os.path.abspath(args.out or config.TFLITE_MODEL_PATH)

    if not os.path.isfile(keras_path):
        raise SystemExit("Keras model not found: %s" % keras_path)

    import tensorflow as tf

    try:
        model = tf.keras.models.load_model(keras_path, compile=False, safe_mode=False)
    except TypeError:
        model = tf.keras.models.load_model(keras_path, compile=False)

    converter = tf.lite.TFLiteConverter.from_keras_model(model)
    converter.optimizations = [tf.lite.Optimize.DEFAULT]
    tflite_model = converter.convert()

    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with open(out_path, "wb") as f:
        f.write(tflite_model)

    print("Wrote:", out_path, "(%d bytes)" % len(tflite_model))


if __name__ == "__main__":
    main()
