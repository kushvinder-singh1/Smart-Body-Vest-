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
_CLEANED_CSV = os.path.join(BASE_DIR, "cleaned_dataset.csv")


def _resolve_dataset_path():
    """
    Training data file. Precedence:
    1) MODULE2_DATASET env
    2) vest_training_combined.csv
    3) cleaned_dataset.csv
    4) datsettt.csv
    5) datsettt.xlsx
    6) augmented / default dummy CSV
    """
    env = os.environ.get("MODULE2_DATASET", "").strip()
    if env:
        p = env if os.path.isabs(env) else os.path.join(BASE_DIR, env)
        if os.path.isfile(p):
            return p
    if os.path.isfile(_COMBINED_CSV):
        return _COMBINED_CSV
    if os.path.isfile(_CLEANED_CSV):
        return _CLEANED_CSV
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
# Legacy column names in some CSVs — not used as model inputs
COL_PAD1 = "pad1_pwm_0_100"
COL_PAD2 = "pad2_pwm_0_100"
COL_AGE = "age_years"
COL_HEIGHT_CM = "height_cm"
COL_WEIGHT_KG = "weight_kg"
COL_GENDER = "gender_0_1"
COL_PAD_LEVEL = "pad_level"
# Derived in data_prep (not in raw CSV): order matches
# [temp, temp_delta, pulse, motion, age, height, weight, gender, temp_step, pulse_step]
COL_TEMP_DELTA = "temp_delta"
COL_TEMP_STEP = "temp_step"
COL_PULSE_STEP = "pulse_step"

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
# Sequence model: base features + consecutive-step Δtemp / Δpulse (clipped in data_prep)
FEATURE_COLS_SEQ = FEATURE_COLS + [COL_TEMP_STEP, COL_PULSE_STEP]
FEATURE_INDEX = {name: i for i, name in enumerate(FEATURE_COLS)}
FEATURE_DIM = len(FEATURE_COLS)
FEATURE_DIM_SEQ = len(FEATURE_COLS_SEQ)

PAD_LEVEL_CLASSES = ("OFF", "LOW", "MEDIUM", "HIGH")
NUM_PAD_CLASSES = len(PAD_LEVEL_CLASSES)

SHUFFLE_SEED = 42

SEQ_LENGTH = 24
EPOCHS_CLASSIFIER = 80
BATCH_SIZE_CLASSIFIER = 32

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

# Real-time pad_level smoothing (majority of last N predictions after safety)
PREDICTION_SMOOTH_WINDOW = 3

# Sensor ranges for inference (before scaling); outside → fallback (not model)
SENSOR_TEMP_MIN_C = 20.0
SENSOR_TEMP_MAX_C = 45.0
# Training data: clip/report body temp to this band before labels + features
TEMP_TRAINING_CLIP_MIN_C = 20.0
TEMP_TRAINING_CLIP_MAX_C = 45.0
# In-memory synthetic expansion (see synthetic_dataset.generate_temperature_coverage_synthetic)
SYNTHETIC_TEMP_RANGE_MIN_C = 33.0
SYNTHETIC_TEMP_RANGE_MAX_C = 38.0
DEFAULT_SYNTHETIC_APPEND_ROWS = 24000
SENSOR_PULSE_MIN_BPM = 30.0
SENSOR_PULSE_MAX_BPM = 200.0

# Firebase / logs (override at runtime via env MODULE2_MODEL_VERSION in get_model_version_tag)
MODEL_VERSION_DEFAULT = "tflite_v2"

# Min softmax probability to trust model; else temperature fallback
MODEL_CONFIDENCE_MIN = 0.5

# Reset rolling buffer if no new samples for this many seconds
BUFFER_STALE_SECONDS = 5.0

SCALER_FEATURES_PATH = os.path.join(DATA_DIR, "scaler_features.pkl")
SCALER_TARGET_PATH = os.path.join(DATA_DIR, "scaler_target.pkl")
CLASSIFIER_MODEL_PATH = os.path.join(MODELS_DIR, "pad_level_classifier.keras")
TFLITE_MODEL_PATH = os.path.join(MODELS_DIR, "pad_level_classifier.tflite")

FIREBASE_PATH_SENSORS = "sensors/latest"
FIREBASE_PATH_COMMAND = "heating/command"
FIREBASE_PATH_USER_PROFILE = "user/profile"

DEFAULT_AGE_YEARS = 28.0
DEFAULT_HEIGHT_CM = 170.0
DEFAULT_WEIGHT_KG = 70.0
DEFAULT_GENDER_0_1 = 0.5
