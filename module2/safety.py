"""
Phase 4 — Safety overrides after ML/fallback pad_level (OFF / LOW / MEDIUM / HIGH).

PWM paths removed.
"""
from __future__ import annotations

from typing import Union

from . import config


def adjust_pad_level_after_prediction(
    temp_c: Union[float, None],
    pulse_bpm: Union[float, None],
    level: str,
) -> str:
    """
    Post-process pad_level (order matches product spec).

    1. temp >= 40 → OFF
    2. pulse >= 150 → OFF
    3. temp <= 34 → HIGH
    4. temp >= 39 OR temp <= 35 → OFF
    5. pulse >= 120 → HIGH→MEDIUM, MEDIUM→LOW
    """
    out = (level or "OFF").strip().upper()
    if out not in config.PAD_LEVEL_CLASSES:
        out = "OFF"

    if temp_c is not None:
        if float(temp_c) >= 40.0:
            return "OFF"

    if pulse_bpm is not None and float(pulse_bpm) >= 150.0:
        return "OFF"

    if temp_c is not None:
        if float(temp_c) <= 34.0:
            out = "HIGH"

    if temp_c is not None:
        t = float(temp_c)
        if t >= 39.0 or t <= 35.0:
            return "OFF"

    if pulse_bpm is not None and float(pulse_bpm) >= 120.0:
        if out == "HIGH":
            out = "MEDIUM"
        elif out == "MEDIUM":
            out = "LOW"

    return out


def is_safe(temp_c, pulse_bpm, sensor_temp_ok=True, sensor_pulse_ok=True, age_years=None):
    """Return True if no safety violation (thresholds from config)."""
    del age_years
    if not sensor_temp_ok or not sensor_pulse_ok:
        return False
    if temp_c is not None:
        if float(temp_c) >= config.TEMP_MAX_SAFE_C or float(temp_c) <= config.TEMP_MIN_SAFE_C:
            return False
    if pulse_bpm is not None:
        if float(pulse_bpm) >= config.PULSE_MAX_SAFE_BPM or float(pulse_bpm) <= config.PULSE_MIN_SAFE_BPM:
            return False
    return True
