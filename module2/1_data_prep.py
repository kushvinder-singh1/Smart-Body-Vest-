"""
Phase 1 — Data preparation.
Load and explore dataset, normalize (MinMaxScaler), create time sequences for LSTM.
"""
import os
import pickle
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.preprocessing import MinMaxScaler

from . import config

def load_and_explore():
    """Load CSV and return DataFrame. Plot temperature over time, pad vs temp, distributions."""
    df = pd.read_csv(config.DATASET_PATH)
    df[config.COL_TIMESTAMP] = pd.to_datetime(df[config.COL_TIMESTAMP])
    print("Dataset shape:", df.shape)
    print(df.describe())
    print("\nMissing:", df.isnull().sum())

    # 1) Temperature over time
    fig, ax = plt.subplots(figsize=(12, 4))
    ax.plot(df.index, df[config.COL_TEMP], alpha=0.7)
    ax.set_xlabel("Sample index")
    ax.set_ylabel("Body temperature (°C)")
    ax.set_title("Temperature over time")
    plt.tight_layout()
    plt.savefig(os.path.join(config.PLOTS_DIR, "01_temperature_over_time.png"), dpi=120)
    plt.close()
    print("Saved: 01_temperature_over_time.png")

    # 2) Heating pad values vs temperature
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    axes[0].scatter(df[config.COL_PAD1], df[config.COL_TEMP], alpha=0.3, s=5)
    axes[0].set_xlabel("Pad1 PWM")
    axes[0].set_ylabel("Temperature (°C)")
    axes[0].set_title("Pad1 vs temperature")
    axes[1].scatter(df[config.COL_PAD2], df[config.COL_TEMP], alpha=0.3, s=5)
    axes[1].set_xlabel("Pad2 PWM")
    axes[1].set_ylabel("Temperature (°C)")
    axes[1].set_title("Pad2 vs temperature")
    plt.tight_layout()
    plt.savefig(os.path.join(config.PLOTS_DIR, "02_pads_vs_temperature.png"), dpi=120)
    plt.close()
    print("Saved: 02_pads_vs_temperature.png")

    # 3) Distributions
    fig, axes = plt.subplots(2, 3, figsize=(12, 8))
    for i, col in enumerate(config.FEATURE_COLS):
        r, c = i // 3, i % 3
        axes[r, c].hist(df[col].dropna(), bins=50, edgecolor="black", alpha=0.7)
        axes[r, c].set_title(col)
    axes[1, 2].axis("off")
    plt.tight_layout()
    plt.savefig(os.path.join(config.PLOTS_DIR, "03_distributions.png"), dpi=120)
    plt.close()
    print("Saved: 03_distributions.png")

    return df

def normalize_data(df):
    """MinMaxScaler for temperature, pulse, motion, pad1, pad2. Save scalers."""
    X = df[config.FEATURE_COLS].values
    y = df[config.TARGET_COL].values.reshape(-1, 1)

    scaler_X = MinMaxScaler()
    scaler_y = MinMaxScaler()
    X_scaled = scaler_X.fit_transform(X)
    y_scaled = scaler_y.fit_transform(y)

    with open(config.SCALER_FEATURES_PATH, "wb") as f:
        pickle.dump(scaler_X, f)
    with open(config.SCALER_TARGET_PATH, "wb") as f:
        pickle.dump(scaler_y, f)
    print("Saved scalers to", config.DATA_DIR)

    return X_scaled, y_scaled, scaler_X, scaler_y

def create_sequences(X, y, seq_length=None):
    """
    Create (samples, seq_length, features) and target next_temperature.
    """
    seq_length = seq_length or config.SEQ_LENGTH
    X_seq, y_seq = [], []
    for i in range(len(X) - seq_length):
        X_seq.append(X[i : i + seq_length])
        y_seq.append(y[i + seq_length, 0])
    return np.array(X_seq), np.array(y_seq)

def run():
    """Run full Phase 1: load, explore, normalize, create sequences, save numpy arrays."""
    df = load_and_explore()
    X_scaled, y_scaled, scaler_X, scaler_y = normalize_data(df)
    X_seq, y_seq = create_sequences(X_scaled, y_scaled)
    print("Sequence shape:", X_seq.shape, "Target shape:", y_seq.shape)
    # Save for training
    np.save(os.path.join(config.DATA_DIR, "X_seq.npy"), X_seq)
    np.save(os.path.join(config.DATA_DIR, "y_seq.npy"), y_seq)
    # Also save full scaled X, y for DNN training (we use current + predicted + motion + pulse)
    np.save(os.path.join(config.DATA_DIR, "X_scaled.npy"), X_scaled)
    np.save(os.path.join(config.DATA_DIR, "y_scaled.npy"), y_scaled)
    return X_seq, y_seq, scaler_X, scaler_y

if __name__ == "__main__":
    run()
