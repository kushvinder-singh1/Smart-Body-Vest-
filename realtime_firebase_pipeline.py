#!/usr/bin/env python3
"""
Firebase → rolling sensor buffer → StandardScaler (saved) → Conv1D TFLite pad_level → safety → output.

Sensors (temp, pulse, motion) + user profile; no scaler refit at inference.

Run from project root:
  python realtime_firebase_pipeline.py

Requires: firebase-admin, tensorflow, scikit-learn, numpy; .tflite from ``python tflite_convert.py``.
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")
os.environ.setdefault("TF_ENABLE_ONEDNN_OPTS", "0")

ROOT = str(Path(__file__).resolve().parent)
sys.path.insert(0, ROOT)


def _load_all_dotenv() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    for path in (
        Path(ROOT) / ".env",
        Path(ROOT) / "module2" / ".env",
        Path(ROOT) / "dashboard" / ".env",
    ):
        load_dotenv(path, override=False)
    if not os.environ.get("FIREBASE_DB_URL", "").strip():
        v = os.environ.get("VITE_FIREBASE_DATABASE_URL", "").strip()
        if v:
            os.environ["FIREBASE_DB_URL"] = v


_load_all_dotenv()

try:
    from module2 import config
except ImportError as exc:
    raise SystemExit("Run from project root so `module2` is importable: %s" % exc) from exc

try:
    import firebase_admin
    from firebase_admin import credentials, db
except ImportError:
    firebase_admin = None
    credentials = None
    db = None

from module2.inference_utils import (
    PadLevelProbabilitySmoother,
    assert_feature_order_matches_config,
    clip_sensors_for_buffer,
    fallback_pad_level_from_temp,
    get_model_version_tag,
    load_scaler_features_only,
    pad_level_from_index,
    sensors_in_sanity_range,
    validate_raw_feature_matrix,
)
from module2.rolling_buffer import RollingFeatureBuffer
from module2.safety import adjust_pad_level_after_prediction
from module2.tflite_pad_inference import PadLevelTfliteInterpreter

LABELS: Tuple[str, ...] = tuple(config.PAD_LEVEL_CLASSES)

LOOP_DELAY_SEC = float(os.environ.get("PIPELINE_LOOP_DELAY_SEC", "0.75"))
HEARTBEAT_SEC = float(os.environ.get("PIPELINE_HEARTBEAT_SEC", "10"))
DEBUG_EVERY_SEC = float(os.environ.get("PIPELINE_DEBUG_EVERY_SEC", "5"))

SMOOTH_WINDOW = max(1, int(os.environ.get("PIPELINE_SMOOTH_WINDOW", str(config.PREDICTION_SMOOTH_WINDOW))))
DEDUPE_READS = os.environ.get("PIPELINE_DEDUPE_SENSOR_READS", "0").strip().lower() in (
    "1",
    "true",
    "yes",
)

OUT_OF_RANGE_MODE = os.environ.get("PIPELINE_OUT_OF_RANGE_MODE", "clip").strip().lower()
if OUT_OF_RANGE_MODE not in ("clip", "ignore"):
    OUT_OF_RANGE_MODE = "clip"

_DEFAULT_READ_PATHS = os.environ.get(
    "FIREBASE_READ_PATHS",
    getattr(config, "FIREBASE_PATH_SENSORS", "sensors/latest") + ",sensor,heating",
)
READ_PATHS: List[str] = [p.strip().strip("/") for p in _DEFAULT_READ_PATHS.split(",") if p.strip()]
WRITE_PATH = os.environ.get("FIREBASE_HEATING_WRITE_PATH", "heating").strip().strip("/") or "heating"


def _probs_from_pad_level(name: str) -> np.ndarray:
    p = np.zeros(config.NUM_PAD_CLASSES, dtype=np.float64)
    try:
        i = list(config.PAD_LEVEL_CLASSES).index((name or "OFF").strip().upper())
    except ValueError:
        i = 0
    p[i] = 1.0
    return p


def _to_number(v: Any) -> Optional[float]:
    if v is None:
        return None
    if isinstance(v, (int, float)):
        if not np.isfinite(float(v)):
            return None
        return float(v)
    if isinstance(v, str):
        s = v.strip()
        if not s:
            return None
        try:
            x = float(s)
            return x if np.isfinite(x) else None
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
    if not isinstance(payload, dict):
        return {}
    sensor = payload.get("sensor", payload)
    if not isinstance(sensor, dict):
        sensor = payload
    temp = _to_number(sensor.get(config.COL_TEMP, sensor.get("temp")))
    pulse = _to_number(sensor.get(config.COL_PULSE, sensor.get("pulse")))
    motion = _to_number(sensor.get(config.COL_MOTION, sensor.get("motion")))
    if motion is None:
        md = sensor.get("motion_detected")
        if isinstance(md, bool):
            motion = 1.0 if md else 0.0
    age = _to_number(sensor.get(config.COL_AGE, sensor.get("age")))
    height = _to_number(sensor.get(config.COL_HEIGHT_CM, sensor.get("height")))
    weight = _to_number(sensor.get(config.COL_WEIGHT_KG, sensor.get("weight")))
    gender = _to_gender_numeric(sensor.get(config.COL_GENDER, sensor.get("gender")))
    return {
        "temp": temp,
        "pulse": pulse,
        "motion_level_0_1": motion,
        "age_years": age,
        "height_cm": height,
        "weight_kg": weight,
        "gender_0_1": gender,
    }


def resolve_credentials_file(raw: str) -> Optional[Path]:
    raw = (raw or "").strip()
    if not raw:
        return None
    p = Path(raw.replace("\\", "/")).expanduser()
    if p.is_file():
        return p.resolve()
    for base in (Path(ROOT), Path(ROOT) / "module2", Path.cwd()):
        cand = (base / p).resolve()
        if cand.is_file():
            return cand
    return None


def find_firebase_admin_json() -> Optional[Path]:
    for folder in (Path(ROOT), Path(ROOT) / "module2"):
        for p in sorted(folder.glob("*firebase-adminsdk*.json")):
            if p.is_file():
                return p.resolve()
    return None


def init_firebase() -> bool:
    if firebase_admin is None or credentials is None or db is None:
        return False
    if firebase_admin._apps:
        return True
    raw = os.environ.get("FIREBASE_CREDENTIALS", "").strip()
    cred_path: Optional[Path] = None
    if raw:
        cred_path = resolve_credentials_file(raw)
    if cred_path is None:
        cred_path = find_firebase_admin_json()
    if cred_path is None:
        cred_path = resolve_credentials_file("serviceAccountKey.json")

    url = os.environ.get("FIREBASE_DB_URL", "").strip()
    if not url:
        url = os.environ.get("VITE_FIREBASE_DATABASE_URL", "").strip()
        if url:
            os.environ["FIREBASE_DB_URL"] = url

    if not url or cred_path is None or not cred_path.is_file():
        return False
    try:
        firebase_admin.initialize_app(
            credentials.Certificate(str(cred_path)),
            {"databaseURL": url},
        )
        return True
    except Exception:
        return False


def diagnose_firebase() -> str:
    if firebase_admin is None:
        return "pip install firebase-admin python-dotenv"
    if not os.environ.get("FIREBASE_DB_URL", "").strip() and not os.environ.get(
        "VITE_FIREBASE_DATABASE_URL", ""
    ).strip():
        return "Set FIREBASE_DB_URL (or VITE_FIREBASE_DATABASE_URL) in .env"
    found = find_firebase_admin_json()
    if not found:
        return "No *firebase-adminsdk*.json; set FIREBASE_CREDENTIALS=path/to.json"
    return "Check DB URL / JSON."


def load_scaler_and_tflite() -> Tuple[Any, PadLevelTfliteInterpreter, Path, Path]:
    scaler_path = Path(config.SCALER_FEATURES_PATH)
    tflite_path = Path(config.TFLITE_MODEL_PATH)
    if not tflite_path.is_file():
        raise FileNotFoundError(
            "TFLite model missing: %s — train then: python tflite_convert.py" % tflite_path
        )
    scaler = load_scaler_features_only(str(scaler_path))
    interp = PadLevelTfliteInterpreter(str(tflite_path))
    return scaler, interp, scaler_path.resolve(), tflite_path.resolve()


def fetch_profile() -> Dict[str, Any]:
    try:
        ref = db.reference(config.FIREBASE_PATH_USER_PROFILE)
        d = ref.get()
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def fetch_sensor_merged() -> Tuple[Optional[Dict[str, Any]], Optional[str], Optional[Tuple[Any, ...]]]:
    profile = fetch_profile()
    if not READ_PATHS:
        return None, None, None
    for path in READ_PATHS:
        try:
            snap = db.reference(path).get()
        except Exception:
            continue
        if not snap or not isinstance(snap, dict):
            continue
        norm = normalize_sensor_payload(snap)
        temp, pulse = norm.get("temp"), norm.get("pulse")
        if temp is None or pulse is None:
            continue
        if norm.get("age_years") is None:
            norm["age_years"] = _to_number(profile.get(config.COL_AGE, profile.get("age")))
        if norm.get("height_cm") is None:
            norm["height_cm"] = _to_number(
                profile.get(config.COL_HEIGHT_CM, profile.get("height"))
            )
        if norm.get("weight_kg") is None:
            norm["weight_kg"] = _to_number(
                profile.get(config.COL_WEIGHT_KG, profile.get("weight"))
            )
        if norm.get("gender_0_1") is None:
            norm["gender_0_1"] = _to_gender_numeric(
                profile.get(config.COL_GENDER, profile.get("gender"))
            )
        norm["age_years"] = float(
            norm["age_years"] if norm["age_years"] is not None else config.DEFAULT_AGE_YEARS
        )
        norm["height_cm"] = float(
            norm["height_cm"] if norm["height_cm"] is not None else config.DEFAULT_HEIGHT_CM
        )
        norm["weight_kg"] = float(
            norm["weight_kg"] if norm["weight_kg"] is not None else config.DEFAULT_WEIGHT_KG
        )
        norm["gender_0_1"] = float(
            norm["gender_0_1"] if norm["gender_0_1"] is not None else config.DEFAULT_GENDER_0_1
        )
        if norm.get("motion_level_0_1") is None:
            norm["motion_level_0_1"] = 0.0
        motion = float(norm["motion_level_0_1"])
        ts_raw = snap.get(config.COL_TIMESTAMP, snap.get("ts", snap.get("time")))
        fingerprint = (
            ts_raw,
            round(float(temp), 4),
            round(float(pulse), 2),
            round(motion, 2),
        )
        return norm, path, fingerprint
    return None, None, None


def write_pad_level(
    pad_level: str,
    inference_state: str,
    inference_source: str,
    last_sent: Optional[Tuple[Any, ...]],
    latency_ms: float = 0.0,
    model_version: str = "",
) -> Optional[Tuple[Any, ...]]:
    mv = model_version or get_model_version_tag("tflite")
    key = (pad_level, inference_state, inference_source, round(float(latency_ms), 2), mv)
    if last_sent == key:
        return last_sent
    try:
        db.reference(WRITE_PATH).update(
            {
                "pad_level": str(pad_level).upper(),
                "inference_state": inference_state,
                "inference_source": inference_source,
                "model_version": mv,
                "inference_latency_ms": round(float(latency_ms), 2),
            }
        )
        print(
            "Firebase updated: %s pad_level=%s state=%s source=%s latency_ms=%.2f version=%s"
            % (WRITE_PATH, pad_level, inference_state, inference_source, latency_ms, mv),
            flush=True,
        )
        return key
    except Exception as exc:
        print("Firebase write failed: %s" % exc, file=sys.stderr, flush=True)
        return last_sent


def main() -> None:
    assert_feature_order_matches_config()

    try:
        scaler, interp, spath, mpath = load_scaler_and_tflite()
    except Exception as e:
        print("Load failed: %s" % e, file=sys.stderr)
        sys.exit(1)

    if not init_firebase():
        print("Firebase init failed:", diagnose_firebase(), file=sys.stderr)
        sys.exit(1)

    seq_len = int(config.SEQ_LENGTH)
    feat_dim = int(config.FEATURE_DIM_SEQ)
    buf = RollingFeatureBuffer(seq_len)
    smoother = PadLevelProbabilitySmoother(window=SMOOTH_WINDOW)
    model_version = get_model_version_tag("tflite")
    conf_min = float(getattr(config, "MODEL_CONFIDENCE_MIN", 0.5))

    print(
        "TFLite pipeline: model=%s scaler=%s SEQ_LENGTH=%s FEATURE_DIM=%s version=%s"
        % (mpath.name, spath.name, seq_len, feat_dim, model_version),
        flush=True,
    )
    print(
        "Read paths: %s | Write: %s | dedupe_reads=%s"
        % (", ".join(READ_PATHS), WRITE_PATH, DEDUPE_READS),
        flush=True,
    )
    print("Ctrl+C to stop.", flush=True)

    last_sent: Optional[Tuple[Any, ...]] = None
    next_hb = time.monotonic()
    next_dbg = time.monotonic()
    last_fp: Optional[Tuple[Any, ...]] = None

    while True:
        try:
            buf.maybe_reset_if_stale(time.monotonic())
            norm, src, fp = fetch_sensor_merged()
            if norm is None:
                time.sleep(LOOP_DELAY_SEC)
                now = time.monotonic()
                if now >= next_hb:
                    print("[heartbeat] waiting for Firebase sensor data …", flush=True)
                    next_hb = now + HEARTBEAT_SEC
                continue

            if DEDUPE_READS and fp is not None and fp == last_fp:
                time.sleep(LOOP_DELAY_SEC)
                continue
            last_fp = fp

            raw_temp_in = float(norm["temp"])
            raw_pulse_in = float(norm["pulse"])
            motion = float(norm["motion_level_0_1"])
            age = float(norm["age_years"])
            height = float(norm["height_cm"])
            weight = float(norm["weight_kg"])
            gender = float(norm["gender_0_1"])

            invalid = not sensors_in_sanity_range(raw_temp_in, raw_pulse_in, motion)
            if invalid:
                print(
                    "[validate] out-of-range temp=%.3f pulse=%.3f motion=%.3f mode=%s"
                    % (raw_temp_in, raw_pulse_in, motion, OUT_OF_RANGE_MODE),
                    flush=True,
                )
                if OUT_OF_RANGE_MODE == "ignore":
                    level = "OFF"
                    if last_sent:
                        level = last_sent[0]
                    last_sent = write_pad_level(
                        level, "fallback", "tflite", last_sent, 0.0, model_version
                    )
                    time.sleep(LOOP_DELAY_SEC)
                    continue
                temp = float(np.clip(raw_temp_in, config.SENSOR_TEMP_MIN_C, config.SENSOR_TEMP_MAX_C))
                pulse = float(
                    np.clip(raw_pulse_in, config.SENSOR_PULSE_MIN_BPM, config.SENSOR_PULSE_MAX_BPM)
                )
            else:
                temp = raw_temp_in
                pulse = raw_pulse_in

            t, p, m = clip_sensors_for_buffer(temp, pulse, motion)
            sensor_ok = sensors_in_sanity_range(raw_temp_in, raw_pulse_in, motion)

            buf.push_observation(t, p, m, age, height, weight, gender)
            scaled_batch = buf.scaled_window(scaler)

            if scaled_batch is None:
                print(
                    "[buffer] %s/%s steps (WARMUP — no prediction)"
                    % (len(buf), seq_len),
                    flush=True,
                )
                last_sent = write_pad_level(
                    "WARMUP", "warmup", "tflite", last_sent, 0.0, model_version
                )
            else:
                rw = buf.raw_window()
                if rw is not None:
                    validate_raw_feature_matrix(rw)

                latency_ms = 0.0

                if not sensor_ok:
                    fb = fallback_pad_level_from_temp(t)
                    probs = _probs_from_pad_level(fb)
                    inf_state = "fallback"
                else:
                    try:
                        probs, latency_ms = interp.predict_proba_timed(scaled_batch)
                        if float(np.max(probs)) < conf_min:
                            fb = fallback_pad_level_from_temp(t)
                            probs = _probs_from_pad_level(fb)
                            inf_state = "fallback"
                        else:
                            inf_state = "model"
                    except Exception as exc:
                        print("[fallback] TFLite failed:", repr(exc), flush=True)
                        fb = fallback_pad_level_from_temp(t)
                        probs = _probs_from_pad_level(fb)
                        inf_state = "fallback"
                        latency_ms = 0.0

                avg_probs = smoother.smooth_proba(probs)
                k = int(np.argmax(avg_probs))
                ml_level = LABELS[k]
                level = adjust_pad_level_after_prediction(t, raw_pulse_in, ml_level)

                now = time.monotonic()
                if now >= next_dbg:
                    next_dbg = now + DEBUG_EVERY_SEC
                    print("[debug] source=%s" % (src,), flush=True)
                    print("[debug] ML -> %s | after safety -> %s" % (ml_level, level), flush=True)
                    print(
                        "[debug] avg_probs: %s"
                        % dict(zip(LABELS, [float(x) for x in np.asarray(avg_probs).reshape(-1)])),
                        flush=True,
                    )

                last_sent = write_pad_level(
                    level, inf_state, "tflite", last_sent, latency_ms, model_version
                )

        except KeyboardInterrupt:
            print("Stopped.", flush=True)
            return
        except Exception as exc:
            print("Loop error: %r" % (exc,), file=sys.stderr, flush=True)

        now = time.monotonic()
        if now >= next_hb:
            next_hb = now + HEARTBEAT_SEC
            print("[heartbeat] ok (buffer=%s/%s)" % (len(buf), seq_len), flush=True)

        time.sleep(LOOP_DELAY_SEC)


if __name__ == "__main__":
    main()
