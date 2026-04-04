"""
Build ``vest_training_combined.csv``: optional user CSV + stratified 33–38 °C synthetic rows.

Run once before training (optional if you already have a combined CSV):
  python generate_training_csv.py
  python run_module2.py

Env: ``MODULE2_SYNTHETIC_N`` (default 24000) — synthetic row count for temperature coverage.
"""
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

if __name__ == "__main__":
    user_csv = os.path.join(ROOT, "datsettt.csv")
    out = os.path.join(ROOT, "vest_training_combined.csv")
    try:
        n_syn = int(os.environ.get("MODULE2_SYNTHETIC_N", "24000"))
    except ValueError:
        n_syn = 24_000

    from module2.data_prep import (
        _coerce_timestamp,
        _read_tabular,
        ensure_demographic_columns,
        standardize_dataset_columns,
    )
    from module2.synthetic_dataset import merge_user_with_temperature_synthetic

    if os.path.isfile(user_csv):
        raw = _read_tabular(user_csv)
        raw = standardize_dataset_columns(raw)
        raw = _coerce_timestamp(raw)
        raw = ensure_demographic_columns(raw)
        raw.to_csv(user_csv, index=False)
        print("Normalized columns:", user_csv)

    merge_user_with_temperature_synthetic(
        user_path=user_csv if os.path.isfile(user_csv) else user_csv,
        out_path=out,
        n_synthetic=n_syn,
        seed=42,
    )
    print("Wrote:", out)
    if os.path.isfile(user_csv):
        print("Included user file:", user_csv)
    else:
        print("(datsettt.csv not found — synthetic-only export)")
