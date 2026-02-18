"""
Phase 5 — Firebase cloud integration.
Listen for new sensor data → predict → optimize → safety check → write heating command.
"""
import os
import numpy as np

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

def _get_lstm_and_dnn():
    from tensorflow import keras
    lstm = keras.models.load_model(config.LSTM_MODEL_PATH)
    dnn = keras.models.load_model(config.DNN_MODEL_PATH)
    return lstm, dnn

def _get_scalers():
    import pickle
    with open(config.SCALER_FEATURES_PATH, "rb") as f:
        scaler_X = pickle.load(f)
    with open(config.SCALER_TARGET_PATH, "rb") as f:
        scaler_y = pickle.load(f)
    return scaler_X, scaler_y

def process_sensor_data(temp, pulse, motion, pad1, pad2, history_buffer, lstm, dnn, scaler_X, scaler_y):
    """
    One step: append to buffer, predict next temp with LSTM, get DNN PWM, apply safety.
    Returns (pad1_pwm, pad2_pwm, new_buffer).
    """
    row = np.array([[temp, pulse, motion, pad1, pad2]], dtype=np.float32)
    row_scaled = scaler_X.transform(row)
    row_flat = row_scaled[0]

    buffer = list(history_buffer)
    buffer.append(row_flat)
    if len(buffer) > config.SEQ_LENGTH:
        buffer.pop(0)
    if len(buffer) < config.SEQ_LENGTH:
        return 0.0, 0.0, buffer

    X_seq = np.array([buffer], dtype=np.float32)
    pred_scaled = lstm.predict(X_seq, verbose=0)
    pred_temp_norm = float(pred_scaled[0, 0])
    current_temp_norm = row_flat[0]
    motion_norm = row_flat[2]
    pulse_norm = row_flat[1]

    dnn_out = dnn.predict(
        np.array([[current_temp_norm, pred_temp_norm, motion_norm, pulse_norm]], dtype=np.float32),
        verbose=0,
    )
    pwm1 = float(dnn_out[0, 0] * config.PWM_MAX)
    pwm2 = float(dnn_out[0, 1] * config.PWM_MAX)

    temp_c = scaler_y.inverse_transform([[row_flat[0]]])[0, 0]
    pulse_bpm = pulse
    pwm1, pwm2 = safety.apply_safety_overrides(temp_c, pulse_bpm, pwm1, pwm2, sensor_temp_ok=True, sensor_pulse_ok=True)
    return pwm1, pwm2, buffer

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
    lstm, dnn = _get_lstm_and_dnn()
    scaler_X, scaler_y = _get_scalers()
    buffer = []

    def on_sensor_event(event):
        data = event.data
        if not data:
            return
        temp = data.get("body_temperature_C")
        pulse = data.get("pulse_bpm")
        motion = data.get("motion_level_0_1", 0)
        pad1 = data.get("pad1_pwm_0_100", 0)
        pad2 = data.get("pad2_pwm_0_100", 0)
        pwm1, pwm2, new_buf = process_sensor_data(
            temp, pulse, motion, pad1, pad2, buffer, lstm, dnn, scaler_X, scaler_y
        )
        buffer.clear()
        buffer.extend(new_buf)
        write_heating_command(pwm1, pwm2)

    ref = db.reference(config.FIREBASE_PATH_SENSORS)
    print("Firebase listener attached:", config.FIREBASE_PATH_SENSORS, "→", config.FIREBASE_PATH_COMMAND)
    ref.listen(on_sensor_event)
