# IoT-Enabled Smart Body Heater System

An intelligent IoT-based wearable heating system designed to provide adaptive thermal support for elderly individuals and people sensitive to cold environments. The system combines physiological monitoring, cloud-based AI inference, real-time data visualization, and automated heating control to maintain user comfort and safety.

---

## Overview

The Smart Body Heater System continuously monitors body temperature, pulse rate, and motion activity using sensors connected to an ESP32 microcontroller. Sensor data is transmitted to Firebase Realtime Database, where a TensorFlow Lite Conv1D model analyzes physiological patterns and predicts the required heating level.

Based on the prediction and safety rules, the system automatically determines one of four heating states:

* OFF
* LOW
* MEDIUM
* HIGH

A web-based dashboard allows caregivers or users to monitor sensor readings, heating status, and system alerts in real time.

---

## Features

* Real-time physiological monitoring
* ESP32-based IoT architecture
* Firebase Realtime Database integration
* Conv1D Deep Learning model for heating prediction
* TensorFlow Lite deployment
* Automated heating control
* Safety override mechanism
* Real-time web dashboard
* User profile management
* Live temperature and pulse monitoring
* Alert generation and logging

---

## System Architecture

### Edge Layer (ESP32)

* Reads temperature, pulse, and motion sensors
* Preprocesses sensor values
* Sends data to Firebase
* Retrieves latest heating command
* Controls heating pad through MOSFET driver

### Cloud Intelligence Layer

* Firebase Realtime Database stores sensor and user data
* Python backend performs preprocessing
* Sliding-window feature generation
* Conv1D TensorFlow Lite inference
* Safety rule validation
* Heating level generation

### Dashboard Layer

* Built using React and Firebase SDK
* Displays live sensor readings
* Shows heating status
* Provides user profile management
* Visualizes historical trends
* Displays alerts and notifications

---

## Technology Stack

### Hardware

* ESP32 Development Board
* DHT22 Temperature Sensor
* Pulse Sensor
* PIR Motion Sensor
* Heating Pad
* MOSFET Driver Circuit

### Software

#### Frontend

* React
* Vite
* Firebase SDK
* Chart.js

#### Backend

* Python
* TensorFlow
* TensorFlow Lite
* Firebase Admin SDK

#### Database

* Firebase Realtime Database

#### AI/ML

* Conv1D Neural Network
* TensorFlow Lite Inference

---

## Dataset

The model was trained using approximately **40,000 physiological samples** containing:

* Body Temperature
* Pulse Rate
* Motion Activity
* Age
* Height
* Weight
* Gender

Dataset format:

```csv
timestamp,
body_temperature_C,
pulse_bpm,
motion_level_0_1,
age_years,
height_cm,
weight_kg,
gender_0_1,
pad_level
```

---

## AI Model

### Model Type

Conv1D Neural Network

### Input

* 24 time-step sequence
* 10 engineered features

### Output Classes

| Class | Heating Level |
| ----- | ------------- |
| 0     | OFF           |
| 1     | LOW           |
| 2     | MEDIUM        |
| 3     | HIGH          |

### Performance

| Metric            | Value  |
| ----------------- | ------ |
| Accuracy          | 98.21% |
| Balanced Accuracy | 98.21% |
| Macro F1 Score    | 98.21% |
| Weighted F1 Score | 98.21% |

---

## Safety Mechanism

The system prioritizes user safety through rule-based overrides.

### Heating Shutdown Conditions

* Temperature ≥ 39°C
* Pulse Rate > 120 BPM
* Pulse Rate < 50 BPM
* Invalid sensor readings
* Missing sensor data

### Safety Response

* Heating OFF
* Alert generation
* Dashboard notification
* Firebase event logging

---

## Firebase Structure

```text
heating
 ├── pad_level
 ├── level
 ├── inference_source
 ├── inference_state
 ├── inference_latency_ms
 └── model_version

meta
 └── current_user

users
 └── {uid}
      ├── profile
      ├── sensor
      └── status
```

---

## Installation

### Clone Repository

```bash
git clone https://github.com/yourusername/smart-body-heater.git
cd smart-body-heater
```

### Install Frontend Dependencies

```bash
npm install
```

### Run Frontend

```bash
npm run dev
```

### Install Python Dependencies

```bash
pip install -r requirements.txt
```

### Run Backend

```bash
python realtime_firebase_pipeline.py
```

---

## Project Workflow

1. ESP32 collects physiological data
2. Sensor readings are sent to Firebase
3. Backend retrieves latest data
4. Sliding window features are generated
5. Conv1D TFLite model predicts heating level
6. Safety layer validates prediction
7. Heating command is written to Firebase
8. Dashboard updates in real time
9. ESP32 retrieves heating command and controls heating pad

---

## Testing Summary

### Functional Testing

* User Registration
* User Login
* Sensor Data Collection
* Firebase Synchronization
* Dashboard Monitoring
* Heating Automation

### Performance Testing

* 72-hour continuous operation
* 0.04% packet loss

### Safety Testing

* 200 safety override scenarios
* 100% successful detection

---

## Future Enhancements

* Full wearable vest integration
* Edge AI deployment on ESP32
* Mobile application support
* Enhanced battery optimization
* Additional physiological sensors
* Expanded clinical validation

---

Live Demo

🔗 Project Dashboard:
(https://smart-heater-b8aca.web.app/)

---

Authors
Ayush Ghai
Anuvab Mazumder
Debjyoti Dutta
Kushvinder Singh

Department of Computer Applications
Lovely Professional University

---

License

This project is developed for academic and research purposes.
