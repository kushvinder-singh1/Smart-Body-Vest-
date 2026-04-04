#!/usr/bin/env python3
"""
Legacy entry point: delegates to ``realtime_firebase_pipeline`` (TFLite + scaler).

Prefer running directly:
  python realtime_firebase_pipeline.py
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def main() -> None:
    import realtime_firebase_pipeline as rfp

    rfp.main()


if __name__ == "__main__":
    main()
