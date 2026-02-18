"""
Run Module 2 pipeline: Phase 1 → 2 → 3, then Phase 6 simulation.
From project root: python run_module2.py
"""
import sys
import os

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

def main():
    print("Phase 1 — Data preparation")
    from module2.data_prep import run as run_data_prep
    run_data_prep()
    print("\nPhase 2 — LSTM temperature model")
    from module2.lstm_model import run as run_lstm
    run_lstm()
    print("\nPhase 3 — DNN heating optimizer")
    from module2.dnn_optimizer import run as run_dnn
    run_dnn()
    print("\nPhase 6 — Real-time simulation")
    from module2.realtime_simulation import run_simulation
    run_simulation(max_steps=100, verbose=True)

if __name__ == "__main__":
    main()
