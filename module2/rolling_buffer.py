"""
Rolling window of raw feature rows aligned with training (10-D, FEATURE_COLS_SEQ order).

Scaling is applied outside this module, after the full (SEQ_LENGTH, 10) matrix is built.
"""
from __future__ import annotations

from collections import deque
import time
from typing import Deque, Optional

import numpy as np

from . import config
from .inference_utils import validate_raw_feature_matrix, validate_runtime_feature_vector

# Match data_prep: consecutive diffs of temp / pulse, then clip
_TEMP_STEP_CLIP = (-1.0, 1.0)
_PULSE_STEP_CLIP = (-10.0, 10.0)


def _motion_bin(m: float) -> float:
    return 1.0 if float(m) >= 0.5 else 0.0


class RollingFeatureBuffer:
    """Last SEQ_LENGTH observations in training column order (unscaled)."""

    def __init__(self, seq_len: Optional[int] = None) -> None:
        self.seq_len = int(seq_len or config.SEQ_LENGTH)
        self._rows: Deque[np.ndarray] = deque(maxlen=self.seq_len)
        self._last_push_monotonic: Optional[float] = None

    def clear(self) -> None:
        self._rows.clear()
        self._last_push_monotonic = None

    def maybe_reset_if_stale(
        self,
        now_monotonic: Optional[float] = None,
        idle_sec: Optional[float] = None,
    ) -> bool:
        """
        Clear buffer if no push for ``idle_sec`` seconds. Returns True if reset.
        """
        idle_sec = float(idle_sec if idle_sec is not None else config.BUFFER_STALE_SECONDS)
        now = float(now_monotonic if now_monotonic is not None else time.monotonic())
        if self._last_push_monotonic is None:
            return False
        if now - self._last_push_monotonic > idle_sec:
            self.clear()
            return True
        return False

    def __len__(self) -> int:
        return len(self._rows)

    def push_observation(
        self,
        temp: float,
        pulse: float,
        motion: float,
        age: float,
        height: float,
        weight: float,
        gender: float,
    ) -> None:
        motion_b = _motion_bin(motion)
        temp_delta = float(temp) - 36.5
        if not self._rows:
            t_step = 0.0
            p_step = 0.0
        else:
            prev = self._rows[-1]
            t_step = float(np.clip(float(temp) - float(prev[0]), *_TEMP_STEP_CLIP))
            p_step = float(np.clip(float(pulse) - float(prev[2]), *_PULSE_STEP_CLIP))
        row = np.array(
            [
                float(temp),
                temp_delta,
                float(pulse),
                motion_b,
                float(age),
                float(height),
                float(weight),
                float(gender),
                t_step,
                p_step,
            ],
            dtype=np.float64,
        )
        validate_runtime_feature_vector(row)
        self._last_push_monotonic = time.monotonic()
        self._rows.append(row)

    def raw_window(self) -> Optional[np.ndarray]:
        if len(self._rows) < self.seq_len:
            return None
        out = np.stack(list(self._rows), axis=0)
        validate_raw_feature_matrix(out)
        return out

    def scaled_window(self, scaler) -> Optional[np.ndarray]:
        """
        Apply ``scaler.transform`` only (inference must never call ``fit`` on this scaler).
        """
        raw = self.raw_window()
        if raw is None:
            return None
        if raw.shape[1] != config.FEATURE_DIM_SEQ:
            raise ValueError(
                "Raw window columns %s != FEATURE_DIM_SEQ (%s)"
                % (raw.shape[1], config.FEATURE_DIM_SEQ)
            )
        return scaler.transform(raw).astype(np.float32).reshape(
            1, self.seq_len, raw.shape[1]
        )
