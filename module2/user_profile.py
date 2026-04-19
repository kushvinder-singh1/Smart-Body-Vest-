"""
Firebase user profile resolution for real-time inference.

Expected Realtime Database structure:
- meta/current_user/uid -> active user id
- users/{uid}/ -> user profile containing: age_years, height_cm, weight_kg, gender_0_1
"""

from __future__ import annotations

import time
from typing import Any, Dict, Optional, Tuple

from . import config

_PROFILE_CACHE_TTL_SEC = float(getattr(config, "USER_PROFILE_CACHE_TTL_SEC", 5.0))
_cache_uid: Optional[str] = None
_cache_profile: Optional[Dict[str, float]] = None
_cache_monotonic: float = 0.0


def _to_number(v: Any) -> Optional[float]:
    if v is None:
        return None
    if isinstance(v, (int, float)):
        try:
            x = float(v)
        except Exception:
            return None
        return x
    if isinstance(v, str):
        s = v.strip()
        if not s:
            return None
        try:
            return float(s)
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


def _parse_uid(meta_current_user: Any) -> Optional[str]:
    # meta/current_user can be {"uid": "..."} or (less commonly) a direct string.
    if isinstance(meta_current_user, dict):
        uid = meta_current_user.get("uid")
        if isinstance(uid, str) and uid.strip():
            return uid.strip()
        return None
    if isinstance(meta_current_user, str) and meta_current_user.strip():
        return meta_current_user.strip()
    return None


def get_user_profile() -> Dict[str, float]:
    """
    Resolve the active user's profile from Firebase.

    Returns a dict with keys:
      age_years, height_cm, weight_kg, gender_0_1

    Any missing Firebase values fall back to config.DEFAULT_*.
    Never raises (safe for real-time loops).
    """
    defaults = {
        "age_years": float(config.DEFAULT_AGE_YEARS),
        "height_cm": float(config.DEFAULT_HEIGHT_CM),
        "weight_kg": float(config.DEFAULT_WEIGHT_KG),
        "gender_0_1": float(config.DEFAULT_GENDER_0_1),
    }

    try:
        from firebase_admin import db  # type: ignore
    except Exception:
        print("[profile] firebase_admin not available; using defaults:", defaults)
        return dict(defaults)

    uid: Optional[str] = None
    user_data: Any = None
    try:
        meta = db.reference(getattr(config, "FIREBASE_PATH_META_CURRENT_USER", "meta/current_user")).get()
        uid = _parse_uid(meta)
    except Exception as exc:
        print("[profile] failed to read meta/current_user:", repr(exc))
        uid = None

    print("[profile] current uid:", uid)

    if not uid:
        print("[profile] missing uid; using defaults:", defaults)
        return dict(defaults)

    base = getattr(config, "FIREBASE_PATH_USERS", "users").strip().strip("/")

    # Small cache to avoid repeated reads in tight loops.
    global _cache_uid, _cache_profile, _cache_monotonic
    now = time.monotonic()
    if (
        _cache_profile is not None
        and _cache_uid == uid
        and (now - float(_cache_monotonic)) <= float(_PROFILE_CACHE_TTL_SEC)
    ):
        print("[profile] fetched profile (cached):", _cache_profile)
        return dict(_cache_profile)

    try:
        user_data = db.reference(f"{base}/{uid}").get()
    except Exception as exc:
        print("[profile] failed to read users/%s:" % uid, repr(exc))
        user_data = None

    # If UID doesn't exist under /users, switch to the first available user (if any)
    # and sync it back to meta/current_user so frontend+backend stay aligned.
    uid_mismatch = not isinstance(user_data, dict) or not user_data
    if uid_mismatch:
        all_users: Any = None
        try:
            all_users = db.reference(base).get()
        except Exception as exc:
            print("[profile] failed to list users:", repr(exc))
            all_users = None

        if isinstance(all_users, dict) and all_users:
            try:
                resolved_uid = next(iter(all_users.keys()))
            except Exception:
                resolved_uid = None
            if isinstance(resolved_uid, str) and resolved_uid.strip():
                resolved_uid = resolved_uid.strip()
                print(
                    "[profile] UID not found, switching to available UID: %s" % resolved_uid
                )
                uid = resolved_uid
                try:
                    db.reference(
                        getattr(config, "FIREBASE_PATH_META_CURRENT_USER", "meta/current_user")
                    ).update({"uid": resolved_uid})
                except Exception as exc:
                    print("[profile] failed to auto-sync uid to meta/current_user:", repr(exc))
                try:
                    user_data = db.reference(f"{base}/{uid}").get()
                except Exception as exc:
                    print("[profile] failed to read users/%s:" % uid, repr(exc))
                    user_data = None
            else:
                user_data = None
        else:
            user_data = None

    if not isinstance(user_data, dict) or not user_data:
        print("[profile] missing user data for uid=%s; using defaults:" % uid, defaults)
        return dict(defaults)

    print("[profile] RAW user_data:", user_data)
    if isinstance(user_data, dict) and "profile" in user_data:
        user_data = user_data.get("profile")
    print("[profile] NORMALIZED user_data:", user_data)

    if not isinstance(user_data, dict) or not user_data:
        print("[profile] missing/invalid normalized profile for uid=%s; using defaults:" % uid, defaults)
        return dict(defaults)

    # Support both Firebase field formats:
    # - current: age/height/weight/gender
    # - legacy/expected: age_years/height_cm/weight_kg/gender_0_1
    age = _to_number(user_data.get("age") or user_data.get("age_years"))
    height = _to_number(user_data.get("height") or user_data.get("height_cm"))
    weight = _to_number(user_data.get("weight") or user_data.get("weight_kg"))
    gender = _to_gender_numeric(user_data.get("gender") or user_data.get("gender_0_1"))

    out = {
        "age_years": float(age) if age is not None else defaults["age_years"],
        "height_cm": float(height) if height is not None else defaults["height_cm"],
        "weight_kg": float(weight) if weight is not None else defaults["weight_kg"],
        "gender_0_1": float(gender) if gender is not None else defaults["gender_0_1"],
    }

    missing_list = []
    if age is None:
        missing_list.append("age_years")
    if height is None:
        missing_list.append("height_cm")
    if weight is None:
        missing_list.append("weight_kg")
    if gender is None:
        missing_list.append("gender_0_1")
    missing: Tuple[str, ...] = tuple(missing_list)
    print("[profile] fetched profile:", out)
    if missing:
        print("[profile] fallback used for:", ", ".join(missing))

    _cache_uid = uid
    _cache_profile = dict(out)
    _cache_monotonic = now
    return out


def get_resolved_uid() -> Optional[str]:
    """
    Best-effort resolved UID for the active user.
    Uses the same UID resolution logic as get_user_profile() via its cache.
    """
    try:
        # Trigger resolution (and auto-sync) if needed.
        _ = get_user_profile()
    except Exception:
        return None
    return _cache_uid

