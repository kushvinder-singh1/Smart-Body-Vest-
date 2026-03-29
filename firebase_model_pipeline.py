#!/usr/bin/env python3
"""
Stream pad level predictions (OFF / LOW / MEDIUM / HIGH) to Firebase Realtime Database.
"""
from __future__ import annotations

import os

# Must be set before TensorFlow / oneDNN initializes (quieter console).
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")
os.environ.setdefault("TF_ENABLE_ONEDNN_OPTS", "0")

import glob
import pickle
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

def _load_all_dotenv() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    for path in (
        os.path.join(ROOT, ".env"),
        os.path.join(ROOT, "module2", ".env"),
        os.path.join(ROOT, "dashboard", ".env"),
    ):
        load_dotenv(path, override=False)
    # Dashboard only defines VITE_FIREBASE_DATABASE_URL
    if not os.environ.get("FIREBASE_DB_URL", "").strip():
        v = os.environ.get("VITE_FIREBASE_DATABASE_URL", "").strip()
        if v:
            os.environ["FIREBASE_DB_URL"] = v


_load_all_dotenv()

try:
    from module2 import config as _project_config
except ImportError:
    _project_config = None

try:
    import firebase_admin
    from firebase_admin import credentials, db
except ImportError:
    firebase_admin = None

LABELS = ("OFF", "LOW", "MEDIUM", "HIGH")
LOOP_DELAY_SEC = float(os.environ.get("PIPELINE_LOOP_DELAY_SEC", "0.75"))
HEATING_REF = os.environ.get("FIREBASE_HEATING_PATH", "heating").strip().strip("/") or "heating"
HEARTBEAT_SEC = float(os.environ.get("PIPELINE_HEARTBEAT_SEC", "10"))


def _models_dir() -> str:
    d = os.environ.get("MODELS_DIR", "").strip()
    if d:
        return d if os.path.isabs(d) else os.path.join(ROOT, d)
    if _project_config:
        return _project_config.MODELS_DIR
    return os.path.join(ROOT, "models")


def _scaler_path() -> str:
    p = os.environ.get("SCALER_PATH", "").strip()
    if p:
        return p if os.path.isabs(p) else os.path.join(ROOT, p)
    if _project_config and os.path.isfile(getattr(_project_config, "SCALER_FEATURES_PATH", "")):
        return _project_config.SCALER_FEATURES_PATH
    return os.path.join(ROOT, "data", "scaler_features.pkl")


def _seq_len() -> int:
    if os.environ.get("SEQ_LENGTH"):
        return int(os.environ["SEQ_LENGTH"])
    if _project_config:
        return int(getattr(_project_config, "SEQ_LENGTH", 24))
    return 24


def _feature_dim_seq() -> int:
    if os.environ.get("FEATURE_DIM_SEQ"):
        return int(os.environ["FEATURE_DIM_SEQ"])
    if _project_config:
        return int(getattr(_project_config, "FEATURE_DIM_SEQ", 10))
    return 10


def _ordered_model_paths(models_dir: str) -> List[str]:
    seen: set[str] = set()
    out: List[str] = []

    def add(path: Optional[str]) -> None:
        if not path or not os.path.isfile(path):
            return
        rp = os.path.normpath(os.path.abspath(path))
        if rp not in seen:
            seen.add(rp)
            out.append(rp)

    env_m = os.environ.get("MODEL_PATH", "").strip()
    if env_m:
        add(env_m if os.path.isabs(env_m) else os.path.join(ROOT, env_m))

    for name in (
        "pad_level_classifier.keras",
        "pad_level_classifier.h5",
        "pad_level_classifier_best.joblib",
        "pad_level_classifier.joblib",
        "pad_level_classifier.pkl",
        "model.keras",
        "model.h5",
    ):
        add(os.path.join(models_dir, name))

    globs: List[str] = []
    for pat in (
        "*pad*level*.keras",
        "*pad*level*.h5",
        "*pad*level*.joblib",
        "*pad*level*.pkl",
        "*classifier*.keras",
        "*classifier*.h5",
        "*classifier*.joblib",
        "*classifier*.pkl",
    ):
        globs.extend(glob.glob(os.path.join(models_dir, pat)))
    for p in sorted(globs):
        add(p)

    rest: List[Tuple[int, str]] = []
    for ext in ("*.keras", "*.h5", "*.joblib", "*.pkl"):
        for p in glob.glob(os.path.join(models_dir, ext)):
            bn = os.path.basename(p).lower()
            tier = 0 if ("classifier" in bn or "pad_level" in bn or "pad" in bn) else 1
            rest.append((tier, p))
    for _, p in sorted(rest, key=lambda x: (x[0], os.path.basename(x[1]).lower())):
        add(p)

    return out


def load_model() -> Tuple[str, Any, Optional[Any], str]:
    """
    Returns (backend, model, scaler_or_none, path).
    backend: 'keras' | 'bundle' | 'sklearn'
    """
    import logging

    logging.getLogger("tensorflow").setLevel(logging.ERROR)
    logging.getLogger("keras").setLevel(logging.ERROR)

    models_dir = _models_dir()
    last_err: Optional[Exception] = None

    for path in _ordered_model_paths(models_dir):
        ext = os.path.splitext(path)[1].lower()
        try:
            if ext in (".keras", ".h5", ".hdf5"):
                from module2.keras_load import load_keras_model_for_inference

                m = load_keras_model_for_inference(path)
                sp = _scaler_path()
                if not os.path.isfile(sp):
                    raise FileNotFoundError(f"scaler not found: {sp}")
                with open(sp, "rb") as f:
                    scaler = pickle.load(f)
                return "keras", m, scaler, path

            if ext == ".joblib":
                import joblib

                obj = joblib.load(path)
                backend = _sklearn_backend(obj)
                return backend, obj, None, path

            if ext == ".pkl":
                obj = None
                try:
                    import joblib

                    obj = joblib.load(path)
                except Exception:
                    with open(path, "rb") as f:
                        obj = pickle.load(f)
                backend = _sklearn_backend(obj)
                return backend, obj, None, path
        except Exception as e:
            last_err = e
            continue

    raise RuntimeError(f"No loadable model under {models_dir}. Last error: {last_err}")


def _sklearn_backend(obj: Any) -> str:
    if hasattr(obj, "pipeline") and callable(getattr(obj, "predict_proba", None)):
        return "bundle"
    if callable(getattr(obj, "predict_proba", None)):
        return "sklearn"
    raise ValueError("Pickled object has no usable predict_proba")


def get_sensor_data() -> Dict[str, float]:
    """Swap this for sensors, serial, or an upstream Firebase read."""
    base = float(os.environ.get("DEMO_TEMP_C", "36.0"))
    t = time.time()
    return {
        "temp": base + 0.02 * np.sin(t / 10.0),
        "pulse": 72.0,
        "motion": 0.0,
        "age": float(os.environ.get("DEFAULT_AGE", "28")),
        "height": float(os.environ.get("DEFAULT_HEIGHT_CM", "170")),
        "weight": float(os.environ.get("DEFAULT_WEIGHT_KG", "70")),
        "gender": float(os.environ.get("DEFAULT_GENDER", "0.5")),
    }


def _label_from_probs(probs: np.ndarray) -> str:
    a = np.asarray(probs).reshape(-1)
    if a.size == 0 or not np.all(np.isfinite(a)):
        return "OFF"
    idx = int(np.argmax(a))
    if 0 <= idx < len(LABELS):
        return LABELS[idx]
    return "OFF"


def predict(backend: str, model: Any, scaler: Optional[Any], sensors: Dict[str, float]) -> str:
    try:
        t = float(sensors["temp"])
        p = float(sensors["pulse"])
        motion = 1.0 if float(sensors.get("motion", 0)) >= 0.5 else 0.0
        age = float(sensors.get("age", 28))
        height = float(sensors.get("height", 170))
        weight = float(sensors.get("weight", 70))
        gender = float(sensors.get("gender", 0.5))

        if backend == "keras":
            if scaler is None:
                return "OFF"
            td = t - 36.5
            row = np.array(
                [[t, td, p, motion, age, height, weight, gender, 0.0, 0.0]],
                dtype=np.float64,
            )
            if row.shape[1] != _feature_dim_seq():
                return "OFF"
            row_s = scaler.transform(row)
            seq = np.tile(row_s.astype(np.float32), (1, _seq_len(), 1))
            probs = model.predict(seq, verbose=0)[0]
            return _label_from_probs(probs)

        if backend == "bundle":
            probs = model.predict_proba(t, p, motion, age, height, weight, gender)
            return _label_from_probs(probs)

        if backend == "sklearn":
            try:
                probs = model.predict_proba(t, p, motion, age, height, weight, gender)
            except TypeError:
                from module2.pad_level_ml_pipeline import build_feature_row

                X = build_feature_row(t, p, motion, age, height, weight, gender)
                probs = model.predict_proba(X)[0]
            return _label_from_probs(probs)
    except Exception:
        pass
    return "OFF"


def _resolve_credentials_path(raw: str) -> str:
    """Prefer project root, then module2/, then cwd (relative paths in .env)."""
    raw = raw.strip()
    if not raw:
        return ""
    if os.path.isabs(raw) and os.path.isfile(raw):
        return raw
    for base in (ROOT, os.path.join(ROOT, "module2"), os.getcwd()):
        p = os.path.join(base, raw)
        if os.path.isfile(p):
            return p
    return os.path.join(ROOT, raw)


def _find_firebase_admin_json() -> Optional[str]:
    """Use any *firebase-adminsdk*.json in repo root or module2/."""
    for folder in (ROOT, os.path.join(ROOT, "module2")):
        for p in sorted(glob.glob(os.path.join(folder, "*firebase-adminsdk*.json"))):
            if os.path.isfile(p):
                return p
    return None


def send_to_firebase(level: str, last_sent: Optional[str]) -> Optional[str]:
    """Writes {\"heating\": {\"level\": <label>}}; returns updated last_sent on success."""
    if last_sent == level:
        return last_sent
    try:
        db.reference(HEATING_REF).set({"level": level})
        print(f"Firebase updated: heating/level = {level}", flush=True)
        return level
    except Exception as exc:
        print(f"Firebase write failed: {exc}", file=sys.stderr, flush=True)
        return last_sent


def init_firebase() -> bool:
    if firebase_admin is None:
        return False
    if firebase_admin._apps:
        return True
    raw = os.environ.get("FIREBASE_CREDENTIALS", "").strip()
    cred_path = ""
    if raw:
        cred_path = _resolve_credentials_path(raw)
    if not cred_path or not os.path.isfile(cred_path):
        found = _find_firebase_admin_json()
        if found:
            cred_path = found
    if not cred_path or not os.path.isfile(cred_path):
        cred_path = _resolve_credentials_path("serviceAccountKey.json")

    url = os.environ.get("FIREBASE_DB_URL", "").strip()
    if not url:
        url = os.environ.get("VITE_FIREBASE_DATABASE_URL", "").strip()
        if url:
            os.environ["FIREBASE_DB_URL"] = url

    if not url or not os.path.isfile(cred_path):
        return False
    try:
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred, {"databaseURL": url})
        return True
    except Exception:
        return False


def _diagnose_firebase_init() -> str:
    if firebase_admin is None:
        return "Install: pip install firebase-admin"
    if not os.environ.get("FIREBASE_DB_URL", "").strip() and not os.environ.get(
        "VITE_FIREBASE_DATABASE_URL", ""
    ).strip():
        return "Set FIREBASE_DB_URL or VITE_FIREBASE_DATABASE_URL in .env"
    cred = os.environ.get("FIREBASE_CREDENTIALS", "").strip()
    path = _resolve_credentials_path(cred) if cred else ""
    if cred and os.path.isfile(path):
        return f"Certificate path resolves but init failed: {path}"
    found = _find_firebase_admin_json()
    if not found:
        return (
            "No Admin SDK JSON found. Place *firebase-adminsdk*.json in project root or module2/, "
            "or set FIREBASE_CREDENTIALS in .env"
        )
    return f"Using {found} but initialize_app raised (check DB URL / JSON validity)."


def main() -> None:
    try:
        backend, model, scaler, mpath = load_model()
    except Exception as e:
        print(f"Model load failed: {e}", file=sys.stderr)
        sys.exit(1)

    if not init_firebase():
        print("Firebase init failed:", _diagnose_firebase_init(), file=sys.stderr)
        sys.exit(1)

    print(
        f"Running: backend={backend} model={os.path.basename(mpath)} "
        f"path={HEATING_REF!r} delay={LOOP_DELAY_SEC}s (Ctrl+C to stop)",
        flush=True,
    )

    last_sent: Optional[str] = None
    next_hb = time.monotonic()
    while True:
        try:
            sensors = get_sensor_data()
            level = predict(backend, model, scaler, sensors)
        except Exception:
            level = "OFF"
        last_sent = send_to_firebase(level, last_sent)
        now = time.monotonic()
        if now >= next_hb:
            print(
                f"[heartbeat] predicted={level} last_written={last_sent}",
                flush=True,
            )
            next_hb = now + HEARTBEAT_SEC
        time.sleep(LOOP_DELAY_SEC)


if __name__ == "__main__":
    main()
