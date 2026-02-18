# Module 2 — Cloud-Based Intelligent Thermal Control

## Project description (for documentation)

**Module 2** implements a cloud-based intelligent thermal control system for a smart heating vest. It processes real-time physiological and environmental data using **time-series prediction (LSTM)** and **deep neural network optimization (DNN)**. The system predicts future body temperature trends and dynamically adjusts heating pad activation levels while ensuring **safety thresholds** are maintained. The module integrates with **Firebase** for real-time communication between the wearable hardware (Module 3) and the monitoring dashboard (Module 4).

---

## Structure

```
smart heating prediction/
├── smart_heating_vest_dummy_dataset_20000.csv   # Dataset
├── requirements.txt
├── run_module2.py                               # Run full pipeline (Phase 1→2→3→6)
├── data/                                         # Created: scalers, X_seq.npy, y_seq.npy
├── models/                                       # Created: LSTM + DNN saved models
├── plots/                                        # Created: exploration + LSTM evaluation
└── module2/
    ├── config.py         # Paths, constants, safety thresholds
    ├── data_prep.py      # Phase 1: load, explore, normalize, sequences
    ├── lstm_model.py     # Phase 2: LSTM temperature prediction
    ├── dnn_optimizer.py  # Phase 3: DNN heating optimization
    ├── safety.py               # Phase 4: safety overrides
    ├── firebase_bridge.py      # Phase 5: Firebase listen → predict → command
    └── realtime_simulation.py  # Phase 6: simulate live pipeline
```

---

## To-Do list (implementation status)

| Phase | Task | Status |
|-------|------|--------|
| **1** | Load and explore dataset; plot temp over time, pads vs temp, distributions | ✅ |
| **1** | Normalize (MinMaxScaler): temp, pulse, motion, pad1, pad2 | ✅ |
| **1** | Create time sequences: last 20 timesteps → next temperature | ✅ |
| **2** | Build LSTM(64) + Dropout(0.2) + Dense(32, relu) + Dense(1) | ✅ |
| **2** | Train 20–30 epochs, MSE; save model; plot predicted vs real, RMSE | ✅ |
| **3** | DNN inputs: current temp, predicted temp, motion, pulse | ✅ |
| **3** | DNN outputs: pad1, pad2 (sigmoid × 100 = PWM %) | ✅ |
| **4** | Safety: temp > 39°C → shutdown; pulse > 120 → reduce; sensor missing → shutdown | ✅ |
| **5** | Firebase: listen for sensor data → predict → optimize → safety → write command | ✅ |
| **6** | Real-time simulation: dataset row → AI → command (no hardware) | ✅ |

---

## How to run

1. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Full pipeline (train + simulate)**
   ```bash
   python run_module2.py
   ```
   This runs: Data prep → LSTM train → DNN train → Real-time simulation.

3. **Individual phases** (from project root)
   ```bash
   python -m module2.data_prep
   python -m module2.lstm_model
   python -m module2.dnn_optimizer
   python -m module2.realtime_simulation
   ```

4. **Cloud (Firebase)**  
   See **[CLOUD_SETUP.md](CLOUD_SETUP.md)** for credentials and database layout. Then:
   ```bash
   python run_firebase_listener.py
   ```

---

## Thresholds (config)

All safety and control limits are in **`module2/config.py`**:

| Threshold | Default | Meaning |
|-----------|---------|---------|
| `TEMP_MIN_SAFE_C` | 35.0 | Below → shutdown (sensor error / cold) |
| `TEMP_MAX_SAFE_C` | 39.0 | At or above → shutdown (overheating) |
| `TEMP_COMFORT_LOW_C` / `TEMP_COMFORT_HIGH_C` | 36.0 / 37.5 | Comfort range (for UI/logging) |
| `PULSE_MIN_SAFE_BPM` | 40 | Below → shutdown (sensor error) |
| `PULSE_MAX_SAFE_BPM` | 120 | At or above → reduce heating |
| `PULSE_REDUCE_FACTOR` | 0.5 | Multiply PWM by this when pulse high |
| `PWM_MAX` / `PWM_MIN_SAFE` | 100 / 0 | Output clamp |

Change these in `config.py` to tune behavior.

---

## Safety logic (override AI)

- **Sensor missing** → shutdown  
- **Temp ≥ TEMP_MAX_SAFE_C** or **≤ TEMP_MIN_SAFE_C** → shutdown  
- **Pulse ≥ PULSE_MAX_SAFE_BPM** → reduce heating by `PULSE_REDUCE_FACTOR`  
- **Pulse ≤ PULSE_MIN_SAFE_BPM** → shutdown  

Implemented in **`module2/safety.py`** and applied in the Firebase bridge and simulation.
