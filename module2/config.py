"""
Module 2 — Configuration and constants.
"""
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATASET_PATH = os.path.join(BASE_DIR, "smart_heating_vest_dummy_dataset_20000.csv")
DATA_DIR = os.path.join(BASE_DIR, "data")
MODELS_DIR = os.path.join(BASE_DIR, "models")
PLOTS_DIR = os.path.join(BASE_DIR, "plots")

for d in (DATA_DIR, MODELS_DIR, PLOTS_DIR):
    os.makedirs(d, exist_ok=True)

COL_TIMESTAMP = "timestamp"
COL_TEMP = "body_temperature_C"
COL_PULSE = "pulse_bpm"
COL_MOTION = "motion_level_0_1"
COL_PAD1 = "pad1_pwm_0_100"
COL_PAD2 = "pad2_pwm_0_100"

FEATURE_COLS = [COL_TEMP, COL_PULSE, COL_MOTION, COL_PAD1, COL_PAD2]
TARGET_COL = COL_TEMP

SEQ_LENGTH = 20
LSTM_UNITS = 64
LSTM_DROPOUT = 0.2
DENSE_UNITS = 32
EPOCHS = 25
BATCH_SIZE = 64
VALIDATION_SPLIT = 0.2

DNN_HIDDEN = [64, 32]
DNN_OUTPUT_DIM = 2
PWM_MAX = 100.0

# ---------- THRESHOLDS (safety & control) ----------
# Temperature (°C)
TEMP_MIN_SAFE_C = 35.0          # Below: treat as sensor error or cold emergency
TEMP_MAX_SAFE_C = 39.0          # At or above: shutdown all pads (overheating)
TEMP_COMFORT_LOW_C = 36.0       # Target range low (for logging/UI)
TEMP_COMFORT_HIGH_C = 37.5      # Target range high

# Pulse (bpm)
PULSE_MIN_SAFE_BPM = 40         # Below: possible sensor error
PULSE_MAX_SAFE_BPM = 120        # At or above: reduce heating (safety)
PULSE_REDUCE_FACTOR = 0.5       # Multiply pad PWM by this when pulse >= PULSE_MAX_SAFE_BPM

# Heating output (PWM % 0–100)
PWM_MIN_SAFE = 0.0              # Floor after safety overrides

SCALER_FEATURES_PATH = os.path.join(DATA_DIR, "scaler_features.pkl")
SCALER_TARGET_PATH = os.path.join(DATA_DIR, "scaler_target.pkl")
LSTM_MODEL_PATH = os.path.join(MODELS_DIR, "lstm_temperature.keras")
DNN_MODEL_PATH = os.path.join(MODELS_DIR, "dnn_heating_optimizer.keras")

# Firebase Realtime Database paths (cloud integration)
FIREBASE_PATH_SENSORS = "sensors/latest"   # ESP32 writes here
FIREBASE_PATH_COMMAND = "heating/command"   # Module 2 writes pad1, pad2 here
