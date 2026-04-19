"""
Phase 5 — Firebase: rolling buffer → scaler.transform only → TFLite → safety → probability smooth.

No scaler fit at inference. Buffer not full → pad_level WARMUP.
"""
import os
import time

import numpy as np
from typing import Any, Dict, Optional, Tuple

from . import config
from . import safety
from .inference_utils import (
    PadLevelProbabilitySmoother,
    clip_sensors_for_buffer,
    fallback_pad_level_from_temp,
    get_model_version_tag,
    load_scaler_features_only,
    pad_level_from_index,
    sensors_in_sanity_range,
    validate_raw_feature_matrix,
    validate_sequence_batch_shape,
)
from .rolling_buffer import RollingFeatureBuffer
from .user_profile import get_user_profile

# Load .env from project root if python-dotenv available
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(config.BASE_DIR, ".env"))
except ImportError:
    pass

try:
    import firebase_admin
    from firebase_admin import credentials, db
    FIREBASE_AVAILABLE = True
except ImportError:
    firebase_admin = None
    credentials = None
    db = None
    FIREBASE_AVAILABLE = False


def _probs_from_pad_level(name: str) -> np.ndarray:
    name = (name or "OFF").strip().upper()
    p = np.zeros(config.NUM_PAD_CLASSES, dtype=np.float64)
    try:
        i = list(config.PAD_LEVEL_CLASSES).index(name)
    except ValueError:
        i = 0
    p[i] = 1.0
    return p


def _get_predictor_and_scaler():
    scaler_X = load_scaler_features_only()
    if not os.path.isfile(config.TFLITE_MODEL_PATH):
        raise FileNotFoundError(
            "TFLite model not found: %s — run training then: python tflite_convert.py"
            % config.TFLITE_MODEL_PATH
        )
    from .tflite_pad_inference import load_pad_level_tflite

    return load_pad_level_tflite(), scaler_X, "tflite"


def process_sensor_data(
    temp: float,
    pulse: float,
    motion: float,
    age: float,
    height: float,
    weight: float,
    gender: float,
    buf: RollingFeatureBuffer,
    predictor,
    scaler_X,
    smoother: PadLevelProbabilitySmoother,
    model_version: str,
) -> Tuple[str, str, str, float]:
    """
    Returns (pad_level, inference_state, inference_source, latency_ms).

    inference_state: model | fallback | warmup
    inference_source: tflite (deployment)
    """
    del model_version  # reserved for Firebase payload at call site
    try:
        raw_temp = float(temp)
        raw_pulse = float(pulse)
        raw_motion = float(motion)

        t, p, m = clip_sensors_for_buffer(raw_temp, raw_pulse, raw_motion)
        sensor_ok = sensors_in_sanity_range(raw_temp, raw_pulse, raw_motion)

        buf.push_observation(t, p, m, float(age), float(height), float(weight), float(gender))
        scaled = buf.scaled_window(scaler_X)
        if scaled is None:
            return "WARMUP", "warmup", "tflite", 0.0

        validate_sequence_batch_shape(scaled, config.SEQ_LENGTH, config.FEATURE_DIM_SEQ)
        rw = buf.raw_window()
        if rw is not None:
            validate_raw_feature_matrix(rw)

        latency_ms = 0.0
        conf_min = float(getattr(config, "MODEL_CONFIDENCE_MIN", 0.5))

        if not sensor_ok:
            fb = fallback_pad_level_from_temp(t)
            probs = _probs_from_pad_level(fb)
            inf_state = "fallback"
        else:
            try:
                probs, latency_ms = predictor.predict_proba_timed(scaled)
                if float(np.max(probs)) < conf_min:
                    fb = fallback_pad_level_from_temp(t)
                    probs = _probs_from_pad_level(fb)
                    inf_state = "fallback"
                else:
                    inf_state = "model"
            except Exception as exc:
                print("Inference failed; temperature fallback:", repr(exc))
                fb = fallback_pad_level_from_temp(t)
                probs = _probs_from_pad_level(fb)
                inf_state = "fallback"
                latency_ms = 0.0

        avg_probs = smoother.smooth_proba(probs)
        k = int(np.argmax(avg_probs))
        level = pad_level_from_index(k)
        level = safety.adjust_pad_level_after_prediction(t, raw_pulse, level)
        return level, inf_state, "tflite", float(latency_ms)
    except Exception as exc:
        print("process_sensor_data error (fallback):", repr(exc))
        try:
            fb = fallback_pad_level_from_temp(float(temp))
            probs = _probs_from_pad_level(fb)
            avg = smoother.smooth_proba(probs)
            k = int(np.argmax(avg))
            level = pad_level_from_index(k)
            level = safety.adjust_pad_level_after_prediction(float(temp), float(pulse), level)
            return level, "fallback", "tflite", 0.0
        except Exception:
            return "OFF", "fallback", "tflite", 0.0


def init_firebase(cred_path=None, database_url=None):
    """Initialize Firebase using service account JSON. Cred path can be absolute or relative to project root."""
    if not FIREBASE_AVAILABLE:
        return False
    if firebase_admin._apps:
        return True
    cred_path = cred_path or os.environ.get("FIREBASE_CREDENTIALS", "serviceAccountKey.json")
    if not os.path.isabs(cred_path):
        cred_path = os.path.join(config.BASE_DIR, cred_path)
    if not os.path.isfile(cred_path):
        return False
    database_url = database_url or os.environ.get("FIREBASE_DB_URL", "")
    if not database_url:
        return False
    cred = credentials.Certificate(str(cred_path))
    firebase_admin.initialize_app(cred, {"databaseURL": database_url})
    return True


def _to_number(v: Any) -> Optional[float]:
    """Convert strings/numbers to float; return None if not convertible."""
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        v = v.strip()
        if not v:
            return None
        try:
            return float(v)
        except ValueError:
            return None
    return None


def _to_gender_numeric(v: Any) -> Optional[float]:
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        s = v.strip().lower()
        if s in ("male", "m", "man", "boy"):
            return 1.0
        if s in ("female", "f", "woman", "girl"):
            return 0.0
        return _to_number(v)
    return None


def normalize_sensor_payload(payload: Any) -> Dict[str, Any]:
    """
    Normalize sensor payload (temperature, pulse, motion, demographics only).
    """
    if not isinstance(payload, dict):
        return {}

    sensor = payload.get("sensor", payload)
    if not isinstance(sensor, dict):
        sensor = payload

    temp = _to_number(sensor.get("body_temperature_C", sensor.get("temp")))
    pulse = _to_number(sensor.get("pulse_bpm", sensor.get("pulse")))
    battery = _to_number(sensor.get("battery_percent", sensor.get("battery")))
    motion = _to_number(sensor.get("motion_level_0_1", sensor.get("motion")))
    if motion is None:
        motion_bool = sensor.get("motion_detected")
        if isinstance(motion_bool, bool):
            motion = 1.0 if motion_bool else 0.0
    age = _to_number(sensor.get("age_years", sensor.get("age")))
    height = _to_number(sensor.get("height_cm", sensor.get("height")))
    weight = _to_number(sensor.get("weight_kg", sensor.get("weight")))
    gender = _to_gender_numeric(sensor.get("gender_0_1", sensor.get("gender")))

    return {
        "temp": temp,
        "pulse": pulse,
        "battery_percent": battery,
        "motion_level_0_1": motion,
        "age_years": age,
        "height_cm": height,
        "weight_kg": weight,
        "gender_0_1": gender,
    }


def write_pad_level_command(
    pad_level: str,
    inference_state: str,
    inference_source: str,
    latency_ms: float = 0.0,
    model_version: str = "",
) -> None:
    """Write pad_level and deployment metadata."""
    if not FIREBASE_AVAILABLE:
        return
    ref = db.reference(config.FIREBASE_PATH_COMMAND)
    mv = model_version or get_model_version_tag("unknown")
    ref.set(
        {
            "pad_level": str(pad_level).upper(),
            "inference_state": inference_state,
            "inference_source": inference_source,
            "model_version": mv,
            "inference_latency_ms": round(float(latency_ms), 2),
        }
    )


def listen_and_process():
    """
    Listen for sensor data → pad_level prediction (TFLite preferred) → Firebase command.
    """
    if not init_firebase():
        print("Firebase not configured; use real-time simulation instead.")
        return
    predictor, scaler_X, backend = _get_predictor_and_scaler()
    model_version = get_model_version_tag(backend)
    buf = RollingFeatureBuffer()
    smoother = PadLevelProbabilitySmoother(window=config.PREDICTION_SMOOTH_WINDOW)
    print("Inference backend:", backend, "| model_version:", model_version)
    print("TFLite:", config.TFLITE_MODEL_PATH)
    print("Scaler (inference only):", config.SCALER_FEATURES_PATH)

    sensor_paths = []
    for p in (config.FIREBASE_PATH_SENSORS, "sensor"):
        if p and p not in sensor_paths:
            sensor_paths.append(p)

    last_processed = {"temp": None, "pulse": None}

    def handle_sensor_payload(payload: Any):
        buf.maybe_reset_if_stale(time.monotonic())
        norm = normalize_sensor_payload(payload)
        temp = norm.get("temp")
        pulse = norm.get("pulse")

        if temp is None or pulse is None:
            print("Skipping payload (missing temp/pulse):", payload)
            return

        if last_processed["temp"] == temp and last_processed["pulse"] == pulse:
            return
        last_processed["temp"] = temp
        last_processed["pulse"] = pulse

        print(f"Sensor received: temp={temp:.2f}C pulse={pulse}bpm")

        motion = norm.get("motion_level_0_1")
        if motion is None:
            battery = norm.get("battery_percent")
            motion = (battery / 100.0) if battery is not None else 0.5
        motion = 1.0 if float(motion) >= 0.5 else 0.0

        profile = get_user_profile()
        age = norm.get("age_years")
        height = norm.get("height_cm")
        weight = norm.get("weight_kg")
        gender = norm.get("gender_0_1")
        # Prefer per-payload demographics if present; otherwise use Firebase-resolved profile.
        age = float(age) if age is not None else float(profile["age_years"])
        height = float(height) if height is not None else float(profile["height_cm"])
        weight = float(weight) if weight is not None else float(profile["weight_kg"])
        gender = float(gender) if gender is not None else float(profile["gender_0_1"])

        level, state, source, latency_ms = process_sensor_data(
            temp,
            pulse,
            motion,
            age,
            height,
            weight,
            gender,
            buf,
            predictor,
            scaler_X,
            smoother,
            model_version,
        )
        write_pad_level_command(level, state, source, latency_ms, model_version)
        print(
            f"Wrote: pad_level={level} state={state} source={source} "
            f"latency_ms={latency_ms:.2f} buffer={len(buf)}/{config.SEQ_LENGTH}"
        )

    def on_sensor_event(event):
        try:
            if not event or not hasattr(event, "data"):
                return
            if not event.data:
                return
            handle_sensor_payload(event.data)
        except Exception as e:
            print("Firebase listener error:", repr(e))

    print(
        "Firebase listener attached to sensor paths:",
        ", ".join(sensor_paths),
        "->",
        config.FIREBASE_PATH_COMMAND,
    )

    for p in sensor_paths:
        try:
            ref = db.reference(p)
            payload = ref.get()
            if payload:
                handle_sensor_payload(payload)
        except Exception as e:
            print("Failed to fetch initial sensor payload for", p, ":", repr(e))

    for p in sensor_paths:
        db.reference(p).listen(on_sensor_event)
