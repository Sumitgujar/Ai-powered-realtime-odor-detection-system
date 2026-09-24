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

// Device identity. Leave empty to derive a stable ID from the ESP8266 chip ID.
#define DEVICE_ID_OVERRIDE ""
#define DEVICE_ID_PREFIX "odor-node"
#define FIRMWARE_VERSION "0.4.0-esp8266"

// Sampling and reconnect timing
#define SAMPLE_INTERVAL_MS 10000UL
#define WIFI_RECONNECT_INTERVAL_MS 5000UL
#define SENSOR_RETRY_INTERVAL_MS 30000UL
#define FIREBASE_LOG_INTERVAL_MS 15000UL
#define ADC_SAMPLE_COUNT 16

// NodeMCU ESP8266 analog input. Do not add another analog pin.
#define MQ135_PIN A0
// ESP8266 Arduino analogRead(A0) returns 0..1023.
#define MQ135_ADC_MAX_COUNT 1023.0f
#define MQ135_SCALE 1.0f
#define MQ135_OFFSET 0.0f

// PIR input. D5 is GPIO14 and is not used by the I2C pins below.
#define PIR_PIN 14
#define PIR_ACTIVE_HIGH true

// BME680/BME68x I2C pins/address.
// NodeMCU D2=GPIO4 is SDA; D1=GPIO5 is SCL.
#define I2C_SDA_PIN 4
#define I2C_SCL_PIN 5
#define BME680_PRIMARY_ADDRESS 0x76
#define BME680_SECONDARY_ADDRESS 0x77

// BME calibration: calibrated = raw * scale + offset.
#define BME_GAS_SCALE 1.0f
#define BME_GAS_OFFSET 0.0f
#define TEMPERATURE_OFFSET_C 0.0f
#define HUMIDITY_OFFSET_PERCENT 0.0f
#define PRESSURE_OFFSET_HPA 0.0f

