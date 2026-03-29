"""
Phase 5 — Firebase cloud integration.
Listen for new sensor data → predict → optimize → safety check → write heating command.
"""
import os
import numpy as np
from typing import Any, Dict, Optional

from . import config
from . import safety

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
    FIREBASE_AVAILABLE = False

def _get_classifier_and_scaler():
    import pickle

    from .keras_load import load_keras_model_for_inference

    clf = load_keras_model_for_inference(config.CLASSIFIER_MODEL_PATH)
    with open(config.SCALER_FEATURES_PATH, "rb") as f:
        scaler_X = pickle.load(f)
    return clf, scaler_X


def process_sensor_data(
    temp,
    pulse,
    motion,
    age,
    height,
    weight,
    gender,
    classifier,
    scaler_X,
):
    """
    pad_level → PWM → safety. Time-series LSTM+DNN: 10-D MinMax row (Δtemp/Δpulse = 0
    without history), tiled to SEQ_LENGTH.
    """
    motion = 1.0 if float(motion) >= 0.5 else 0.0
    temp_delta = float(temp) - 36.5
    row = np.array(
        [
            [
                temp,
                temp_delta,
                pulse,
                motion,
                age,
                height,
                weight,
                gender,
                0.0,
                0.0,
            ]
        ],
        dtype=np.float32,
    )
    row_scaled = scaler_X.transform(row)
    r = np.asarray(row_scaled, dtype=np.float32).reshape(1, -1)
    seq = np.tile(r, (1, config.SEQ_LENGTH, 1))
    probs = classifier.predict(seq, verbose=0)[0]
    k = int(np.argmax(probs))
    pwm1, pwm2 = config.PAD_CLASS_INDEX_TO_PWM[k]
    pwm1, pwm2 = safety.apply_safety_overrides(
        float(temp),
        float(pulse),
        pwm1,
        pwm2,
        sensor_temp_ok=True,
        sensor_pulse_ok=True,
        age_years=age,
    )
    return pwm1, pwm2

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
    cred = credentials.Certificate(cred_path)
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
    Normalize sensor payload for both possible schemas:
    1) { body_temperature_C, pulse_bpm, battery_percent, ... }
    2) { sensor: { temp, pulse, battery, ... } }
    """
    if not isinstance(payload, dict):
        return {}

    # Some clients nest readings under `sensor`.
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
    pad1 = _to_number(sensor.get("pad1_pwm_0_100", sensor.get("pad1")))
    pad2 = _to_number(sensor.get("pad2_pwm_0_100", sensor.get("pad2")))
    age = _to_number(sensor.get("age_years", sensor.get("age")))
    height = _to_number(sensor.get("height_cm", sensor.get("height")))
    weight = _to_number(sensor.get("weight_kg", sensor.get("weight")))
    gender = _to_gender_numeric(sensor.get("gender_0_1", sensor.get("gender")))

    return {
        "temp": temp,
        "pulse": pulse,
        "battery_percent": battery,
        "motion_level_0_1": motion,
        "pad1_pwm_0_100": pad1,
        "pad2_pwm_0_100": pad2,
        "age_years": age,
        "height_cm": height,
        "weight_kg": weight,
        "gender_0_1": gender,
    }

def write_heating_command(pad1_pwm, pad2_pwm):
    if not FIREBASE_AVAILABLE:
        return
    ref = db.reference(config.FIREBASE_PATH_COMMAND)
    ref.set({"pad1": round(pad1_pwm, 1), "pad2": round(pad2_pwm, 1)})

def listen_and_process():
    """
    Listen for new sensor data on Firebase, run prediction + optimization, write command.
    Flow: New sensor data → Predict → Optimize → Safety check → Send to Firebase → ESP32 executes.
    """
    if not init_firebase():
        print("Firebase not configured; use real-time simulation instead.")
        return
    clf, scaler_X = _get_classifier_and_scaler()

    # ESP32 / other clients may write either:
    # - sensors/latest (expected by dashboard)
    # - sensor (what your Firebase console currently shows)
    sensor_paths = []
    for p in (config.FIREBASE_PATH_SENSORS, "sensor"):
        if p and p not in sensor_paths:
            sensor_paths.append(p)

    last_processed = {"temp": None, "pulse": None}
    profile_ref = db.reference(config.FIREBASE_PATH_USER_PROFILE)

    def _load_profile():
        try:
            p = profile_ref.get()
            return p if isinstance(p, dict) else {}
        except Exception:
            return {}

    def handle_sensor_payload(payload: Any):
        norm = normalize_sensor_payload(payload)
        temp = norm.get("temp")
        pulse = norm.get("pulse")

        if temp is None or pulse is None:
            # Without temp/pulse the AI pipeline can't run; keep listener alive.
            print("Skipping payload (missing temp/pulse):", payload)
            return

        # Avoid re-processing identical values (helps when multiple listeners fire).
        if last_processed["temp"] == temp and last_processed["pulse"] == pulse:
            return
        last_processed["temp"] = temp
        last_processed["pulse"] = pulse

        print(f"Sensor received: temp={temp:.2f}C pulse={pulse}bpm")

        # Use binary motion (0/1) from payload when available.
        motion = norm.get("motion_level_0_1")
        if motion is None:
            battery = norm.get("battery_percent")
            motion = (battery / 100.0) if battery is not None else 0.5
        motion = 1.0 if float(motion) >= 0.5 else 0.0

        profile = _load_profile()
        age = norm.get("age_years")
        height = norm.get("height_cm")
        weight = norm.get("weight_kg")
        gender = norm.get("gender_0_1")
        if age is None:
            age = _to_number(profile.get("age_years", profile.get("age")))
        if height is None:
            height = _to_number(profile.get("height_cm", profile.get("height")))
        if weight is None:
            weight = _to_number(profile.get("weight_kg", profile.get("weight")))
        if gender is None:
            gender = _to_gender_numeric(profile.get("gender_0_1", profile.get("gender")))
        age = age if age is not None else config.DEFAULT_AGE_YEARS
        height = height if height is not None else config.DEFAULT_HEIGHT_CM
        weight = weight if weight is not None else config.DEFAULT_WEIGHT_KG
        gender = gender if gender is not None else config.DEFAULT_GENDER_0_1

        pwm1, pwm2 = process_sensor_data(
            temp, pulse, motion, age, height, weight, gender, clf, scaler_X
        )
        write_heating_command(pwm1, pwm2)
        print(f"Wrote command: pad1={pwm1:.1f}% pad2={pwm2:.1f}%")

    def on_sensor_event(event):
        try:
            if not event or not hasattr(event, "data"):
                return
            if not event.data:
                return
            handle_sensor_payload(event.data)
        except Exception as e:
            # Important: don't let unexpected payloads kill the realtime listener.
            print("Firebase listener error:", repr(e))

    print(
        "Firebase listener attached to sensor paths:",
        ", ".join(sensor_paths),
        "->",
        config.FIREBASE_PATH_COMMAND,
    )

    # Process immediately if there's already data at either path.
    for p in sensor_paths:
        try:
            ref = db.reference(p)
            payload = ref.get()
            if payload:
                handle_sensor_payload(payload)
        except Exception as e:
            print("Failed to fetch initial sensor payload for", p, ":", repr(e))

    # Attach listeners for both possible sensor locations.
    for p in sensor_paths:
        db.reference(p).listen(on_sensor_event)
