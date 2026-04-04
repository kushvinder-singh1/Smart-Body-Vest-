#!/usr/bin/env python3
"""
Smoke-test TFLite pad_level classifier: load .tflite and run one random forward pass.

Usage (from project root):
  python tflite_inference.py
  python tflite_inference.py --model models/pad_level_classifier.tflite
"""
from __future__ import annotations

import argparse
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default=None, help="Path to .tflite file")
    args = parser.parse_args()

    import numpy as np

    from module2 import config
    from module2.tflite_pad_inference import PadLevelTfliteInterpreter

    path = os.path.abspath(args.model or config.TFLITE_MODEL_PATH)
    if not os.path.isfile(path):
        raise SystemExit("Missing %s — run training then python tflite_convert.py" % path)

    interp = PadLevelTfliteInterpreter(path)
    sl = int(config.SEQ_LENGTH)
    fd = int(config.FEATURE_DIM_SEQ)
    x = np.random.randn(1, sl, fd).astype(np.float32) * 0.1
    idx = interp.predict_class_index(x)
    probs = interp.predict_proba(x)
    print("Model:", path)
    print("Input shape:", (1, sl, fd))
    print("Argmax class index:", idx, "->", config.PAD_LEVEL_CLASSES[idx])
    print("Probs:", dict(zip(config.PAD_LEVEL_CLASSES, probs.tolist())))


if __name__ == "__main__":
    main()
