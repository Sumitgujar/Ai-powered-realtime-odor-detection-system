#pragma once

#include <Arduino.h>

struct SensorReading {
  String deviceId;
  String timestamp;
  double latitude = 0.0;
  double longitude = 0.0;
  float bmeGas = 0.0f;
  float mq135 = 0.0f;
  float mq136 = 0.0f;
  float mq3 = 0.0f;
  float temperature = 0.0f;
  float humidity = 0.0f;
  float pressure = 0.0f;
  bool gpsAvailable = false;
  bool valid = false;
  uint32_t errorMask = 0;
  uint32_t sequence = 0;
};

enum SensorError : uint32_t {
  SENSOR_OK = 0,
  ERROR_BME_UNAVAILABLE = 1U << 0,
  ERROR_BME_READ = 1U << 1,
  ERROR_MQ135_SATURATED = 1U << 2,
  ERROR_MQ136_SATURATED = 1U << 3,
  ERROR_MQ3_SATURATED = 1U << 4,
  ERROR_GPS_NO_FIX = 1U << 5,
  ERROR_TIME_UNAVAILABLE = 1U << 6,
};
