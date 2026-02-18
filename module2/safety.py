"""
Phase 4 — Safety overrides.
These overrides MUST override AI output. All thresholds from config.
"""
from . import config

def apply_safety_overrides(temp_c, pulse_bpm, pad1_pwm, pad2_pwm, sensor_temp_ok=True, sensor_pulse_ok=True):
    """
    Apply safety rules using config thresholds. Returns (pad1_pwm, pad2_pwm).
    - Sensor missing → shutdown
    - Temp >= TEMP_MAX_SAFE_C → shutdown
    - Temp <= TEMP_MIN_SAFE_C → shutdown (sensor error / cold emergency)
    - Pulse >= PULSE_MAX_SAFE_BPM → reduce by PULSE_REDUCE_FACTOR
    - Pulse <= PULSE_MIN_SAFE_BPM → treat as sensor error, shutdown
    """
    out1, out2 = float(pad1_pwm), float(pad2_pwm)

    if not sensor_temp_ok or not sensor_pulse_ok:
        return config.PWM_MIN_SAFE, config.PWM_MIN_SAFE

    if temp_c is not None:
        if temp_c >= config.TEMP_MAX_SAFE_C:
            return config.PWM_MIN_SAFE, config.PWM_MIN_SAFE
        if temp_c <= config.TEMP_MIN_SAFE_C:
            return config.PWM_MIN_SAFE, config.PWM_MIN_SAFE

    if pulse_bpm is not None:
        if pulse_bpm >= config.PULSE_MAX_SAFE_BPM:
            out1 *= config.PULSE_REDUCE_FACTOR
            out2 *= config.PULSE_REDUCE_FACTOR
        if pulse_bpm <= config.PULSE_MIN_SAFE_BPM:
            return config.PWM_MIN_SAFE, config.PWM_MIN_SAFE

    return (
        max(config.PWM_MIN_SAFE, min(config.PWM_MAX, out1)),
        max(config.PWM_MIN_SAFE, min(config.PWM_MAX, out2)),
    )

def is_safe(temp_c, pulse_bpm, sensor_temp_ok=True, sensor_pulse_ok=True):
    """Return True if no safety violation (all thresholds from config)."""
    if not sensor_temp_ok or not sensor_pulse_ok:
        return False
    if temp_c is not None:
        if temp_c >= config.TEMP_MAX_SAFE_C or temp_c <= config.TEMP_MIN_SAFE_C:
            return False
    if pulse_bpm is not None:
        if pulse_bpm >= config.PULSE_MAX_SAFE_BPM or pulse_bpm <= config.PULSE_MIN_SAFE_BPM:
            return False
    return True
