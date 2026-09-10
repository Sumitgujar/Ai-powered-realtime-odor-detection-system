# AI-Powered Real-Time Odor Detection System

A modular project skeleton for an IoT, machine-learning, cloud, and web system that monitors environmental and gas sensor readings, classifies odor conditions, estimates intensity, detects anomalies, and presents real-time results.

## Architecture

```text
ESP32 sensors → Firebase Realtime Database → FastAPI/Python ML
              → Firebase Realtime Database → React dashboard
```

- **ESP32 firmware** collects sensor readings and sends them to Firebase.
- **Firebase Realtime Database** is the shared real-time data layer; **Firebase Auth** protects access.
- **FastAPI backend** reads sensor records, coordinates ML inference, and writes predictions/anomalies back to Firebase.
- **ML package** contains data preparation, training, evaluation, and model artifacts using pandas, NumPy, scikit-learn, and XGBoost.
- **React dashboard** reads live results and visualizes charts and locations with Recharts and Leaflet.

## Data flow

1. The ESP32 captures gas and environmental measurements.
2. Firmware publishes raw readings to Firebase Realtime Database.
3. The FastAPI application retrieves readings and passes them to the ML layer.
4. The ML layer returns odor class, estimated intensity, and anomaly status.
5. The backend writes processed results to Firebase.
6. The React dashboard displays real-time readings and predictions to authenticated users.

## Configuration

Copy each `.env.example` file to `.env` in the same folder and add local credentials. Never commit `.env` files, Firebase credentials, API keys, or trained models containing sensitive information.

## Current scope

This repository contains architecture and placeholder files only. Feature implementation and Docker configuration are intentionally deferred until the application works locally.
