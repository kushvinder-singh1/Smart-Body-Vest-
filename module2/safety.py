"""
Phase 4 — Safety overrides.
These overrides MUST override AI output. All thresholds from config.
"""
from . import config

def _age_profile(age_years):
    """
    Age-aware safety profile. Lower tolerance for children and elderly.
    Returns (temp_max, pulse_max, pwm_cap_factor).
    """
    try:
        age = float(age_years) if age_years is not None else None
    except (TypeError, ValueError):
        age = None

    if age is None:
        return config.TEMP_MAX_SAFE_C, config.PULSE_MAX_SAFE_BPM, 1.0
    if age < 13:
        return min(config.TEMP_MAX_SAFE_C, 38.0), min(config.PULSE_MAX_SAFE_BPM, 110), 0.65
    if age < 18:
        return min(config.TEMP_MAX_SAFE_C, 38.3), min(config.PULSE_MAX_SAFE_BPM, 115), 0.8
    if age >= 65:
        return min(config.TEMP_MAX_SAFE_C, 38.2), min(config.PULSE_MAX_SAFE_BPM, 110), 0.75
    return config.TEMP_MAX_SAFE_C, config.PULSE_MAX_SAFE_BPM, 1.0

def apply_safety_overrides(temp_c, pulse_bpm, pad1_pwm, pad2_pwm, sensor_temp_ok=True, sensor_pulse_ok=True, age_years=None):
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

    temp_max, pulse_max, pwm_cap_factor = _age_profile(age_years)

    if temp_c is not None:
        if temp_c >= temp_max:
            return config.PWM_MIN_SAFE, config.PWM_MIN_SAFE
        if temp_c <= config.TEMP_MIN_SAFE_C:
            return config.PWM_MIN_SAFE, config.PWM_MIN_SAFE

    if pulse_bpm is not None:
        if pulse_bpm >= pulse_max:
            out1 *= config.PULSE_REDUCE_FACTOR
            out2 *= config.PULSE_REDUCE_FACTOR
        if pulse_bpm <= config.PULSE_MIN_SAFE_BPM:
            return config.PWM_MIN_SAFE, config.PWM_MIN_SAFE

    if pwm_cap_factor < 1.0:
        cap = config.PWM_MAX * pwm_cap_factor
        out1 = min(out1, cap)
        out2 = min(out2, cap)

    return (
        max(config.PWM_MIN_SAFE, min(config.PWM_MAX, out1)),
        max(config.PWM_MIN_SAFE, min(config.PWM_MAX, out2)),
    )

def is_safe(temp_c, pulse_bpm, sensor_temp_ok=True, sensor_pulse_ok=True, age_years=None):
    """Return True if no safety violation (all thresholds from config)."""
    if not sensor_temp_ok or not sensor_pulse_ok:
        return False
    temp_max, pulse_max, _ = _age_profile(age_years)
    if temp_c is not None:
        if temp_c >= temp_max or temp_c <= config.TEMP_MIN_SAFE_C:
            return False
    if pulse_bpm is not None:
        if pulse_bpm >= pulse_max or pulse_bpm <= config.PULSE_MIN_SAFE_BPM:
            return False
    return True
