"""
Add demographic columns to the dummy dataset:
- age_years
- height_cm
- weight_kg
- gender_0_1 (0=female, 1=male)

It assigns stable demographic profiles per synthetic subject block so
time-series continuity stays realistic.
"""
import os
import numpy as np
import pandas as pd

from . import config


def augment_dataset(dataset_path=None, subject_block_size=200):
    # Always augment the shipped dummy CSV, not the active training file (e.g. datsettt.xlsx).
    dataset_path = dataset_path or os.path.join(
        config.BASE_DIR, "smart_heating_vest_dummy_dataset_20000.csv"
    )
    df = pd.read_csv(dataset_path)

    required = [config.COL_AGE, config.COL_HEIGHT_CM, config.COL_WEIGHT_KG, config.COL_GENDER]

    rng = np.random.default_rng(42)
    n = len(df)
    n_subjects = max(1, int(np.ceil(n / subject_block_size)))

    # Balanced age-group sampling (children, teens, adults, seniors).
    age_pool = np.concatenate([
        rng.integers(6, 13, size=max(1, n_subjects // 5)),
        rng.integers(13, 18, size=max(1, n_subjects // 5)),
        rng.integers(18, 41, size=max(1, n_subjects // 5)),
        rng.integers(41, 66, size=max(1, n_subjects // 5)),
        rng.integers(66, 86, size=max(1, n_subjects // 5)),
    ])
    if len(age_pool) < n_subjects:
        age_pool = np.concatenate([age_pool, rng.integers(6, 86, size=n_subjects - len(age_pool))])
    rng.shuffle(age_pool)
    ages = age_pool[:n_subjects]
    heights = np.clip(rng.normal(170.0, 10.0, size=n_subjects), 148.0, 200.0)
    weights = np.clip(rng.normal(72.0, 14.0, size=n_subjects), 45.0, 130.0)
    genders = rng.integers(0, 2, size=n_subjects).astype(float)

    subject_id = np.arange(n) // subject_block_size
    subject_id = np.clip(subject_id, 0, n_subjects - 1)

    df[config.COL_AGE] = ages[subject_id].astype(float)
    df[config.COL_HEIGHT_CM] = np.round(heights[subject_id], 1)
    df[config.COL_WEIGHT_KG] = np.round(weights[subject_id], 1)
    df[config.COL_GENDER] = genders[subject_id]

    # Motion is binary in hardware (0/1). Regenerate with mild age dependence:
    # younger users slightly more active, seniors slightly less active.
    p_active = np.where(df[config.COL_AGE].values >= 65, 0.35, 0.5)
    df[config.COL_MOTION] = (rng.random(n) < p_active).astype(float)

    # -------- Balance temperature classes over time --------
    # Make recurring blocks so train/val/test all contain cold/comfort/hot.
    block = 60
    classes = np.arange(n) // block % 3  # 0=cold, 1=comfort, 2=hot
    age = df[config.COL_AGE].values
    motion = df[config.COL_MOTION].values

    temp = np.zeros(n, dtype=float)
    pulse = np.zeros(n, dtype=float)
    for i in range(n):
        # Slightly lower safe comfort for children/elderly.
        age_shift = -0.15 if (age[i] < 13 or age[i] >= 65) else 0.0
        if classes[i] == 0:  # cold
            t = rng.normal(35.6 + age_shift, 0.22)
            p = rng.normal(74 if motion[i] > 0.5 else 69, 6.0)
        elif classes[i] == 1:  # comfort
            t = rng.normal(36.7 + age_shift, 0.24)
            p = rng.normal(81 if motion[i] > 0.5 else 72, 7.0)
        else:  # hot
            t = rng.normal(38.0 + age_shift, 0.20)
            p = rng.normal(90 if motion[i] > 0.5 else 80, 8.0)
        temp[i] = np.clip(t, 35.1, 38.7)
        pulse[i] = np.clip(p, 48, 118)

    df[config.COL_TEMP] = np.round(temp, 3)
    df[config.COL_PULSE] = np.round(pulse).astype(int)

    # -------- Regenerate pad labels to be consistent with physiology --------
    # Cold -> higher heating, comfort -> medium, hot -> low/off.
    pad1 = np.zeros(n, dtype=float)
    pad2 = np.zeros(n, dtype=float)
    for i in range(n):
        t = temp[i]
        m = motion[i]
        if t < config.TEMP_COMFORT_LOW_C:
            base = 72 - 18 * m  # moving user needs less heating
            spread = 10
        elif t <= config.TEMP_COMFORT_HIGH_C:
            base = 44 - 12 * m
            spread = 9
        else:
            base = 14 - 8 * m
            spread = 7
        # pulse-based moderation
        if pulse[i] > 105:
            base *= 0.55
        p1 = np.clip(rng.normal(base, spread), 0, 100)
        p2 = np.clip(rng.normal(base * rng.uniform(0.9, 1.1), spread), 0, 100)
        pad1[i], pad2[i] = p1, p2

    df[config.COL_PAD1] = np.round(pad1).astype(int)
    df[config.COL_PAD2] = np.round(pad2).astype(int)

    # Keep original columns first, append demographics at the end.
    cols = list(df.columns)
    for c in required:
        cols.remove(c)
    cols.extend(required)
    df = df[cols]

    output_path = dataset_path
    try:
        df.to_csv(output_path, index=False)
    except PermissionError:
        root, ext = os.path.splitext(dataset_path)
        output_path = f"{root}_augmented{ext}"
        df.to_csv(output_path, index=False)
        print(f"Primary dataset was locked; wrote augmented copy instead: {output_path}")
    else:
        print(f"Updated dataset: {output_path}")
    print("Added/updated columns:", ", ".join(required))
    print(df[required].describe())
    # Print class balance diagnostics.
    temp_cold = int((df[config.COL_TEMP] < config.TEMP_COMFORT_LOW_C).sum())
    temp_comf = int(((df[config.COL_TEMP] >= config.TEMP_COMFORT_LOW_C) & (df[config.COL_TEMP] <= config.TEMP_COMFORT_HIGH_C)).sum())
    temp_hot = int((df[config.COL_TEMP] > config.TEMP_COMFORT_HIGH_C).sum())
    print(f"Temperature class counts: cold={temp_cold}, comfort={temp_comf}, hot={temp_hot}")

    def pwm_counts(series):
        low = int((series < 35).sum())
        med = int(((series >= 35) & (series <= 70)).sum())
        high = int((series > 70).sum())
        return low, med, high
    l1, m1, h1 = pwm_counts(df[config.COL_PAD1])
    l2, m2, h2 = pwm_counts(df[config.COL_PAD2])
    print(f"Pad1 class counts: low={l1}, medium={m1}, high={h1}")
    print(f"Pad2 class counts: low={l2}, medium={m2}, high={h2}")


if __name__ == "__main__":
    augment_dataset()
