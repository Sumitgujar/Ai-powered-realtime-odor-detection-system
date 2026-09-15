#pragma once

// Copy this file to config.h and fill local values. config.h is gitignored.

// Wi-Fi
#define WIFI_SSID ""
#define WIFI_PASSWORD ""

// Firebase Authentication and Realtime Database
#define FIREBASE_API_KEY ""
#define FIREBASE_DATABASE_URL "https://YOUR_PROJECT_ID-default-rtdb.firebaseio.com"
#define FIREBASE_USER_EMAIL ""
#define FIREBASE_USER_PASSWORD ""
#define FIREBASE_SENSOR_ROOT "/sensor_readings"

// Device identity. Leave empty to derive a stable ID from the ESP32 MAC address.
#define DEVICE_ID_OVERRIDE ""
#define DEVICE_ID_PREFIX "odor-node"
#define FIRMWARE_VERSION "0.3.0"

// Sampling and reconnect timing
#define SAMPLE_INTERVAL_MS 10000UL
#define WIFI_RECONNECT_INTERVAL_MS 5000UL
#define SENSOR_RETRY_INTERVAL_MS 30000UL
#define FIREBASE_LOG_INTERVAL_MS 15000UL
#define ADC_SAMPLE_COUNT 16

// ESP32 ADC1 pins. ADC2 pins must not be used while Wi-Fi is active.
#define MQ135_PIN 34
#define MQ136_PIN 35
#define MQ3_PIN 32

// BME688 I2C pins/address
#define I2C_SDA_PIN 21
#define I2C_SCL_PIN 22
#define BME688_PRIMARY_ADDRESS 0x76
#define BME688_SECONDARY_ADDRESS 0x77

// Optional GPS on UART2. Set GPS_ENABLED to true when a module is connected.
#define GPS_ENABLED false
#define GPS_RX_PIN 16
#define GPS_TX_PIN 17
#define GPS_BAUD 9600
#define GPS_FIX_MAX_AGE_MS 10000UL

// Used when GPS is disabled or a current fix is unavailable.
#define DEFAULT_LATITUDE 18.5204
#define DEFAULT_LONGITUDE 73.8567

// Basic calibration: calibrated = raw * scale + offset.
#define MQ135_SCALE 1.0f
#define MQ135_OFFSET 0.0f
#define MQ136_SCALE 1.0f
#define MQ136_OFFSET 0.0f
#define MQ3_SCALE 1.0f
#define MQ3_OFFSET 0.0f
#define BME_GAS_SCALE 1.0f
#define BME_GAS_OFFSET 0.0f
#define TEMPERATURE_OFFSET_C 0.0f
#define HUMIDITY_OFFSET_PERCENT 0.0f
#define PRESSURE_OFFSET_HPA 0.0f
