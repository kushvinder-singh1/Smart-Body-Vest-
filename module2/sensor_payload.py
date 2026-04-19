"""
Firebase sensor payload resolution for real-time inference.

Supports both Firebase layouts:
- sensors/latest (legacy/global)
- users/{uid}/sensor (per-user)
"""

from __future__ import annotations

from typing import Any, Dict, Optional


def _to_float(v: Any) -> Optional[float]:
    if v is None:
        return None
    if isinstance(v, (int, float)):
        try:
            return float(v)
        except Exception:
            return None
    if isinstance(v, str):
        s = v.strip()
        if not s:
            return None
        try:
            return float(s)
        except ValueError:
            return None
    return None


def _normalize_sensor_dict(d: Any) -> Optional[Dict[str, float]]:
    """
    Normalize user/legacy sensor dict into:
      { body_temperature_C, pulse_bpm, motion_level_0_1 }
    """
    if not isinstance(d, dict) or not d:
        return None

    # Some payloads may be nested under "sensor".
    sensor = d.get("sensor", d)
    if not isinstance(sensor, dict) or not sensor:
        return None

    # Accept both naming schemes and normalize.
    temp = _to_float(sensor.get("body_temperature_C", sensor.get("temp")))
    pulse = _to_float(sensor.get("pulse_bpm", sensor.get("pulse")))
    motion = _to_float(sensor.get("motion_level_0_1", sensor.get("motion")))

    if temp is None or pulse is None:
        return None

    # Motion is allowed to be missing; treat as 0.0 to keep pipeline running.
    if motion is None:
        motion = 0.0

    return {
        "body_temperature_C": float(temp),
        "pulse_bpm": float(pulse),
        "motion_level_0_1": float(motion),
    }


def get_sensor_payload(uid: Optional[str]) -> Optional[Dict[str, float]]:
    """
    Step 1: Try sensors/latest.
    Step 2: Fallback to users/{uid}/sensor (if uid is available).
    Returns normalized payload or None.
    """
    try:
        from firebase_admin import db  # type: ignore
    except Exception:
        return None

    # Step 1: global sensors/latest
    try:
        snap = db.reference("sensors/latest").get()
        out = _normalize_sensor_dict(snap)
        if out is not None:
            return out
    except Exception:
        pass

    # Step 2: per-user users/{uid}/sensor
    if not uid:
        return None
    try:
        snap = db.reference(f"users/{uid}/sensor").get()
        out = _normalize_sensor_dict(snap)
        if out is not None:
            return out
    except Exception:
        return None

    return None

