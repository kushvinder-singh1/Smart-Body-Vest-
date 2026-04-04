"""
Run Module 2 pipeline: Phase 1 (data prep) → Phase 2 (Conv1D pad_level classifier).

Phase 1: time-ordered rows, temp steps, StandardScaler, sliding windows, optional synthetic
temperature coverage, saved arrays + scaler.

Phase 2: train Conv1D classifier; export TFLite with ``python tflite_convert.py``.

From project root: python run_module2.py
"""
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)


def main() -> None:
    print("Phase 1 — Data preparation")
    from module2.data_prep import run as run_data_prep

    run_data_prep()
    print("\nPhase 2 — Pad level classifier Conv1D (OFF / LOW / MEDIUM / HIGH)")
    from module2.pad_classifier import run as run_classifier

    run_classifier()


if __name__ == "__main__":
    main()
