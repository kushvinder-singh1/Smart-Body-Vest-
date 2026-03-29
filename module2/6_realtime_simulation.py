"""Legacy entry: run from project root. Delegates to realtime_simulation."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from module2.realtime_simulation import run_simulation

if __name__ == "__main__":
    run_simulation(max_steps=200, verbose=True)
