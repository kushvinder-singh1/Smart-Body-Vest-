"""
TensorFlow Lite inference for the pad_level sequence classifier.

Input must be exactly (1, SEQ_LENGTH, FEATURE_DIM_SEQ) float32 — validated on every call.
Output validated as (NUM_PAD_CLASSES,) probabilities / logits.
"""
from __future__ import annotations

import os
import time
from typing import Any, Optional, Tuple

import numpy as np

try:
    import tensorflow as tf
except ImportError:  # pragma: no cover
    tf = None  # type: ignore

from . import config
from .inference_utils import validate_classifier_output_probs, validate_sequence_batch_shape


class PadLevelTfliteInterpreter:
    """Loads .tflite once; reuses allocate_tensors for low overhead."""

    def __init__(self, model_path: str) -> None:
        if tf is None:
            raise ImportError("tensorflow is required for TFLite inference")
        path = os.path.abspath(model_path)
        if not os.path.isfile(path):
            raise FileNotFoundError(path)
        self._interpreter = tf.lite.Interpreter(model_path=path)
        self._interpreter.allocate_tensors()
        self._in = self._interpreter.get_input_details()[0]
        self._out = self._interpreter.get_output_details()[0]
        self._validate_model_signature()

    def _validate_model_signature(self) -> None:
        """Ensure model expects fixed shape (1, SEQ_LENGTH, 10) when dimensions are known."""
        shape = self._in.get("shape")
        if shape is None:
            return
        arr = np.array(shape, dtype=np.int64)
        exp = np.array(
            [1, config.SEQ_LENGTH, config.FEATURE_DIM_SEQ],
            dtype=np.int64,
        )
        for i in range(min(len(arr), len(exp))):
            if arr[i] > 0 and int(arr[i]) != int(exp[i]):
                raise ValueError(
                    "TFLite model input shape %s does not match expected %s"
                    % (list(shape), list(exp))
                )

    @property
    def input_details(self) -> Any:
        return self._in

    @property
    def output_details(self) -> Any:
        return self._out

    def predict_class_index(self, x: np.ndarray) -> int:
        probs, _ = self.predict_proba_timed(x)
        return int(np.argmax(probs))

    def predict_proba(self, x: np.ndarray) -> np.ndarray:
        probs, _ = self.predict_proba_timed(x)
        return probs

    def predict_proba_timed(self, x: np.ndarray) -> Tuple[np.ndarray, float]:
        """Returns (validated probs (4,), latency_ms)."""
        x = np.asarray(x, dtype=np.float32)
        validate_sequence_batch_shape(x, config.SEQ_LENGTH, config.FEATURE_DIM_SEQ)
        t0 = time.perf_counter()
        self._interpreter.set_tensor(self._in["index"], x)
        self._interpreter.invoke()
        out = self._interpreter.get_tensor(self._out["index"])
        raw = np.asarray(out[0], dtype=np.float64).reshape(-1)
        probs = validate_classifier_output_probs(raw)
        latency_ms = (time.perf_counter() - t0) * 1000.0
        return probs, latency_ms


def load_pad_level_tflite(path: Optional[str] = None) -> PadLevelTfliteInterpreter:
    p = path or config.TFLITE_MODEL_PATH
    return PadLevelTfliteInterpreter(p)
