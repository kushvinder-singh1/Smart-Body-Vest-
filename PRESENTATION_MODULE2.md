# What to show in your presentation (Module 2)

## 1. One-sentence description

*“Module 2 is the cloud brain: it takes live sensor data, predicts body temperature with an LSTM, decides heating levels with a DNN, applies safety overrides, and sends commands to the vest via Firebase.”*

---

## 2. Architecture diagram (describe or draw)

```
[ESP32 / Module 3]  →  Firebase  →  [Module 2: Python]
                                          ↓
                                    LSTM → predict temp
                                    DNN  → pad1, pad2
                                    Safety overrides
                                          ↓
[ESP32]  ←  Firebase  ←  heating command (pad1%, pad2%)
```

---

## 3. What to demo

1. **Dataset & exploration**
   - Show `plots/01_temperature_over_time.png`, `02_pads_vs_temperature.png`, `03_distributions.png`.
   - Mention: 20,000 samples, inputs = temp, pulse, motion, pad1, pad2.

2. **LSTM**
   - Show `plots/04_lstm_predicted_vs_real.png` and state RMSE.
   - Say: “We use the last 20 timesteps to predict the next temperature.”

3. **DNN optimizer**
   - Say: “Inputs: current temp, predicted temp, motion, pulse. Outputs: two PWM values 0–100% for the pads.”

4. **Safety**
   - Read the three rules from `4_safety.py`: temp > 39°C → off; pulse > 120 → reduce; sensor missing → off.
   - Emphasize: “Safety always overrides the AI.”

5. **Real-time simulation**
   - Run: `python -m module2.realtime_simulation` (or `python run_module2.py` and show the last part).
   - Show console: “dataset row → predict → optimize → safety → command” with sample outputs.

6. **Firebase** (if connected)
   - Show flow: new sensor document → Python runs LSTM + DNN + safety → writes to `heating/command` → ESP32 executes.

---

## 4. Key phrases for examiners

- **Time-series prediction:** LSTM on last 20 steps to predict next temperature.
- **Optimization:** DNN maps (current temp, predicted temp, motion, pulse) to (pad1, pad2) PWM.
- **Safety overrides:** Hard-coded rules override model output (temp, pulse, sensor checks).
- **End-to-end:** Sensor data → Firebase → Python (predict + optimize + safety) → Firebase → hardware.

---

## 5. File checklist for slides/screen

- `module2/config.py` — safety thresholds (39°C, 120 bpm).
- `module2/safety.py` — override logic.
- `module2/firebase_bridge.py` — listen → process → write command.
- `plots/04_lstm_predicted_vs_real.png` — LSTM performance.
- Console output of `realtime_simulation` — proof the cloud pipeline works.
