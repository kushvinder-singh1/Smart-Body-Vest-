"""
Run Module 2 pipeline: Phase 1 (time-series data prep) → Phase 2 (LSTM+DNN pad_level).

Phase 1 sorts by (session_id, timestamp), adds per-step Δtemp/Δpulse, builds
``X_seq_pad.npy`` (SEQ_LENGTH × 10 features), saves MinMax scaler for inference.
Phase 2 trains Conv1D + BiLSTM + LSTM + dense head (Keras only).

From project root: python run_module2.py
"""
import sys
import os

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)


def main():
    skip_sim = os.environ.get("MODULE2_SKIP_SIM", "1") == "1"
    print("Phase 1 — Data preparation")
    from module2.data_prep import run as run_data_prep
    run_data_prep()
    print("\nPhase 2 — Pad level classifier (OFF / LOW / MEDIUM / HIGH)")
    from module2.pad_classifier import run as run_classifier
    run_classifier()
    if skip_sim:
        print("\nPhase 6 — Real-time simulation (skipped; set MODULE2_SKIP_SIM=0 to run)")
    else:
        print("\nPhase 6 — Real-time simulation")
        from module2.realtime_simulation import run_simulation
        run_simulation(max_steps=100, verbose=True)


if __name__ == "__main__":
    main()
