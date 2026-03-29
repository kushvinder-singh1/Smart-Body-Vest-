"""Keras 3+ blocks Lambda layers unless safe_mode=False; inference does not need compiled loss."""
import os
from typing import Any


def load_keras_model_for_inference(path: str) -> Any:
    from tensorflow import keras

    path = os.path.abspath(path)
    try:
        return keras.models.load_model(path, compile=False, safe_mode=False)
    except TypeError:
        return keras.models.load_model(path, compile=False)
