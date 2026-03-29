"""
Build vest_training_combined.csv: physics-based synthetic sessions + your datsettt.csv.

Run once before training:
  python generate_training_csv.py
  python run_module2.py

Override sizes with env MODULE2_SYNTH_SESSIONS (default 96) and MODULE2_SYNTH_STEPS (default 320).
"""
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

if __name__ == "__main__":
    n_sess = int(os.environ.get("MODULE2_SYNTH_SESSIONS", "96"))
    n_steps = int(os.environ.get("MODULE2_SYNTH_STEPS", "320"))
    user_csv = os.path.join(ROOT, "datsettt.csv")
    out = os.path.join(ROOT, "vest_training_combined.csv")

    from module2.data_prep import load_and_clean_file
    from module2.synthetic_dataset import merge_user_and_synthetic

    if os.path.isfile(user_csv):
        clean_user = load_and_clean_file(user_csv)
        clean_user.to_csv(user_csv, index=False)
        print("Rewrote canonical schema (no pad PWM, motion_level -> motion_level_0_1):", user_csv)

    merge_user_and_synthetic(
        user_path=user_csv,
        out_path=out,
        n_sessions=n_sess,
        steps_per_session=n_steps,
        seed=42,
    )
    print("Wrote:", out)
    if os.path.isfile(user_csv):
        print("Included user file:", user_csv)
    else:
        print("(datsettt.csv not found — synthetic only)")
