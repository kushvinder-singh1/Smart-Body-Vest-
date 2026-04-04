# Module 2 — Cloud-Based Intelligent Thermal Control

## Project description (for documentation)

**Module 2** implements cloud-side inference for a smart heating vest: a **Conv1D** sequence classifier outputs **pad level** (OFF / LOW / MEDIUM / HIGH) from sensor streams, with **TensorFlow Lite** deployment and **Firebase** integration for real-time commands.

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

2. **Train classifier**
   ```bash
   python run_module2.py
   python tflite_convert.py
   ```

3. **Individual phases** (from project root)
   ```bash
   python -m module2.data_prep
   python -m module2.pad_classifier
   ```

4. **Cloud (Firebase)**
   ```bash
   python run_firebase_listener.py
   ```
   or `python realtime_firebase_pipeline.py`

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
