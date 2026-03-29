"""
Module 2 — Configuration and constants.
"""
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DEFAULT_CSV = os.path.join(BASE_DIR, "smart_heating_vest_dummy_dataset_20000.csv")
_AUGMENTED_CSV = os.path.join(BASE_DIR, "smart_heating_vest_dummy_dataset_20000_augmented.csv")
_USER_XLSX = os.path.join(BASE_DIR, "datsettt.xlsx")
_USER_CSV = os.path.join(BASE_DIR, "datsettt.csv")
_COMBINED_CSV = os.path.join(BASE_DIR, "vest_training_combined.csv")


def _resolve_dataset_path():
    """
    Training data file. Precedence:
    1) MODULE2_DATASET env
    2) vest_training_combined.csv
    3) datsettt.csv
    4) datsettt.xlsx
    5) augmented / default dummy CSV
    """
    env = os.environ.get("MODULE2_DATASET", "").strip()
    if env:
        p = env if os.path.isabs(env) else os.path.join(BASE_DIR, env)
        if os.path.isfile(p):
            return p
    if os.path.isfile(_COMBINED_CSV):
        return _COMBINED_CSV
    if os.path.isfile(_USER_CSV):
        return _USER_CSV
    if os.path.isfile(_USER_XLSX):
        return _USER_XLSX
    if os.path.isfile(_AUGMENTED_CSV):
        return _AUGMENTED_CSV
    return _DEFAULT_CSV


DATASET_PATH = _resolve_dataset_path()
DATA_DIR = os.path.join(BASE_DIR, "data")
MODELS_DIR = os.path.join(BASE_DIR, "models")
PLOTS_DIR = os.path.join(BASE_DIR, "plots")

for d in (DATA_DIR, MODELS_DIR, PLOTS_DIR):
    os.makedirs(d, exist_ok=True)

COL_TIMESTAMP = "timestamp"
COL_TEMP = "body_temperature_C"
COL_PULSE = "pulse_bpm"
COL_MOTION = "motion_level_0_1"
# Legacy column names (e.g. augment_dummy_dataset) — not used as model inputs
COL_PAD1 = "pad1_pwm_0_100"
COL_PAD2 = "pad2_pwm_0_100"
COL_AGE = "age_years"
COL_HEIGHT_CM = "height_cm"
COL_WEIGHT_KG = "weight_kg"
COL_GENDER = "gender_0_1"
COL_PAD_LEVEL = "pad_level"
# Derived in data_prep.run (not stored in CSV): helps the model learn heating vs cooling
COL_TEMP_DELTA = "temp_delta_from_36_5"
# Per-timestep deltas within a session (time-series only; zeros at cold start / single row)
COL_TEMP_DELTA_STEP = "temp_delta_step"
COL_PULSE_DELTA_STEP = "pulse_delta_step"

# X: no pad PWM columns — y is pad_level (4-class)
FEATURE_COLS = [
    COL_TEMP,
    COL_TEMP_DELTA,
    COL_PULSE,
    COL_MOTION,
    COL_AGE,
    COL_HEIGHT_CM,
    COL_WEIGHT_KG,
    COL_GENDER,
]
# LSTM / Conv1D input: base features + session-wise Δtemp, Δpulse between consecutive samples
FEATURE_COLS_SEQ = FEATURE_COLS + [COL_TEMP_DELTA_STEP, COL_PULSE_DELTA_STEP]
FEATURE_INDEX = {name: i for i, name in enumerate(FEATURE_COLS)}
FEATURE_DIM = len(FEATURE_COLS)
FEATURE_DIM_SEQ = len(FEATURE_COLS_SEQ)

PAD_LEVEL_CLASSES = ("OFF", "LOW", "MEDIUM", "HIGH")
NUM_PAD_CLASSES = len(PAD_LEVEL_CLASSES)
PAD_CLASS_INDEX_TO_PWM = {
    0: (0.0, 0.0),
    1: (25.0, 25.0),
    2: (50.0, 50.0),
    3: (85.0, 85.0),
}

SHUFFLE_SEED = 42

SEQ_LENGTH = 24
LSTM_UNITS = 80
LSTM_UNITS_2 = 40
LSTM_DROPOUT = 0.2
DENSE_UNITS = 48
EPOCHS = 50
EPOCHS_LSTM = 50
EPOCHS_DNN = 50
EPOCHS_CLASSIFIER = 80
BATCH_SIZE = 64
BATCH_SIZE_CLASSIFIER = 32
VALIDATION_SPLIT = 0.2

CLASSIFIER_HIDDEN = [256, 128, 64]

# ---------- THRESHOLDS (safety & control) ----------
TEMP_MIN_SAFE_C = 35.0
TEMP_MAX_SAFE_C = 39.0
TEMP_COMFORT_LOW_C = 36.0
TEMP_COMFORT_HIGH_C = 37.5

PULSE_MIN_SAFE_BPM = 40
PULSE_MAX_SAFE_BPM = 120
PULSE_REDUCE_FACTOR = 0.5

PWM_MAX = 100.0
PWM_MIN_SAFE = 0.0

SCALER_FEATURES_PATH = os.path.join(DATA_DIR, "scaler_features.pkl")
SCALER_TARGET_PATH = os.path.join(DATA_DIR, "scaler_target.pkl")
CLASSIFIER_MODEL_PATH = os.path.join(MODELS_DIR, "pad_level_classifier.keras")
# Optional sklearn pipeline output (``python -m module2.pad_level_ml_pipeline``) — not used by Firebase
BEST_PAD_CLASSIFIER_BUNDLE_PATH = os.path.join(MODELS_DIR, "pad_level_classifier_best.joblib")
LSTM_MODEL_PATH = os.path.join(MODELS_DIR, "lstm_temperature.keras")
DNN_MODEL_PATH = os.path.join(MODELS_DIR, "dnn_heating_optimizer.keras")

FIREBASE_PATH_SENSORS = "sensors/latest"
FIREBASE_PATH_COMMAND = "heating/command"
FIREBASE_PATH_USER_PROFILE = "user/profile"

DEFAULT_AGE_YEARS = 28.0
DEFAULT_HEIGHT_CM = 170.0
DEFAULT_WEIGHT_KG = 70.0
DEFAULT_GENDER_0_1 = 0.5
