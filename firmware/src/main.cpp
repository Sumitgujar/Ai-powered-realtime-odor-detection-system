#include <Arduino.h>
#include <ESP8266WiFi.h>
#include <Wire.h>
#include <time.h>

#include <Adafruit_BME680.h>
#include <Firebase_ESP_Client.h>

#include "addons/TokenHelper.h"
#include "calibration.h"
#include "sensor_reading.h"

#if __has_include("config.h")
#include "config.h"
#else
#error "Missing include/config.h. Copy include/config.example.h to include/config.h and configure it."
#endif

namespace {
Adafruit_BME680 bme(&Wire);
FirebaseData firebaseData;
FirebaseAuth firebaseAuth;
FirebaseConfig firebaseConfig;

String deviceId;
bool bmeAvailable = false;
bool firebaseStarted = false;
bool timeConfigured = false;
uint32_t readingSequence = 0;
unsigned long lastSampleAt = 0;
unsigned long lastWiFiAttemptAt = 0;
unsigned long lastSensorAttemptAt = 0;
unsigned long lastFirebaseLogAt = 0;
SensorReading pendingReading;
bool hasPendingReading = false;

String buildDeviceId() {
  if (strlen(DEVICE_ID_OVERRIDE) > 0) {
    return String(DEVICE_ID_OVERRIDE);
  }
  char suffix[9];
  snprintf(suffix, sizeof(suffix), "%08X", ESP.getChipId());
  String result = String(DEVICE_ID_PREFIX) + "-" + suffix;
  result.toLowerCase();
  return result;
}

bool configurationLooksValid() {
  const bool valid = strlen(WIFI_SSID) > 0 && strlen(FIREBASE_API_KEY) > 0 &&
                     strlen(FIREBASE_DATABASE_URL) > 0 &&
                     strlen(FIREBASE_USER_EMAIL) > 0 &&
                     strlen(FIREBASE_USER_PASSWORD) > 0;
  if (!valid) {
    Serial.println("[config] Missing Wi-Fi or Firebase values in include/config.h");
  }
  return valid;
}

void connectWiFiIfNeeded() {
  if (WiFi.status() == WL_CONNECTED) {
    return;
  }
  const unsigned long now = millis();
  if (now - lastWiFiAttemptAt < WIFI_RECONNECT_INTERVAL_MS) {
    return;
  }
  lastWiFiAttemptAt = now;
  Serial.printf("[wifi] Connecting to %s\\n", WIFI_SSID);
  WiFi.disconnect();
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
}

void configureTimeIfNeeded() {
  if (timeConfigured || WiFi.status() != WL_CONNECTED) {
    return;
  }
  configTime(0, 0, "pool.ntp.org", "time.google.com");
  timeConfigured = true;
  Serial.println("[time] UTC NTP synchronization requested");
}

String utcTimestamp(bool &valid) {
  const time_t now = time(nullptr);
  if (now < 1704067200) {
    valid = false;
    return String();
  }
  struct tm utcTime {};
  gmtime_r(&now, &utcTime);
  char buffer[25];
  strftime(buffer, sizeof(buffer), "%Y-%m-%dT%H:%M:%SZ", &utcTime);
  valid = true;
  return String(buffer);
}

bool initializeBme() {
  Wire.begin(I2C_SDA_PIN, I2C_SCL_PIN);
  bmeAvailable = bme.begin(BME680_PRIMARY_ADDRESS) ||
                 bme.begin(BME680_SECONDARY_ADDRESS);
  if (!bmeAvailable) {
    Serial.println("[sensor] BME680/BME68x not found at 0x76 or 0x77");
    return false;
  }
  bme.setTemperatureOversampling(BME680_OS_8X);
  bme.setHumidityOversampling(BME680_OS_2X);
  bme.setPressureOversampling(BME680_OS_4X);
  bme.setIIRFilterSize(BME680_FILTER_SIZE_3);
  bme.setGasHeater(320, 150);
  Serial.println("[sensor] BME680/BME68x initialized");
  return true;
}

void retrySensorsIfNeeded() {
  if (bmeAvailable) {
    return;
  }
  const unsigned long now = millis();
  if (now - lastSensorAttemptAt < SENSOR_RETRY_INTERVAL_MS) {
    return;
  }
  lastSensorAttemptAt = now;
  initializeBme();
}

float readAveragedMq135() {
  uint32_t total = 0;
  for (uint8_t index = 0; index < ADC_SAMPLE_COUNT; ++index) {
    total += static_cast<uint32_t>(analogRead(MQ135_PIN));
    delay(2);
  }
  return static_cast<float>(total) / static_cast<float>(ADC_SAMPLE_COUNT);
}

void markMq135Saturation(float value, uint32_t &errorMask) {
  if (value <= 1.0f || value >= MQ135_ADC_MAX_COUNT - 1.0f) {
    errorMask |= ERROR_MQ135_SATURATED;
  }
}

SensorReading collectReading() {
  SensorReading reading;
  reading.deviceId = deviceId;
  reading.sequence = ++readingSequence;
  reading.pirMotion = digitalRead(PIR_PIN) == (PIR_ACTIVE_HIGH ? HIGH : LOW);

  bool timestampValid = false;
  reading.timestamp = utcTimestamp(timestampValid);
  if (!timestampValid) {
    reading.errorMask |= ERROR_TIME_UNAVAILABLE;
    Serial.println("[time] No valid UTC timestamp; sample not published");
    return reading;
  }

  const float mq135Raw = readAveragedMq135();
  reading.mq135 = applyCalibration(
      mq135Raw, MQ135_SCALE, MQ135_OFFSET, 0.0f, MQ135_ADC_MAX_COUNT);
  markMq135Saturation(reading.mq135, reading.errorMask);

  if (!bmeAvailable) {
    reading.errorMask |= ERROR_BME_UNAVAILABLE;
    Serial.println("[sensor] BME680/BME68x unavailable; sample not published");
    return reading;
  }
  if (!bme.performReading()) {
    bmeAvailable = false;
    reading.errorMask |= ERROR_BME_READ;
    Serial.println("[sensor] BME680/BME68x read failed; sample not published");
    return reading;
  }

  reading.temperature = applyCalibration(
      bme.temperature, 1.0f, TEMPERATURE_OFFSET_C, -40.0f, 85.0f);
  reading.humidity = applyCalibration(
      bme.humidity, 1.0f, HUMIDITY_OFFSET_PERCENT, 0.0f, 100.0f);
  reading.pressure = applyCalibration(
      bme.pressure / 100.0f, 1.0f, PRESSURE_OFFSET_HPA, 300.0f, 1100.0f);
  reading.bmeGas = applyCalibration(
      bme.gas_resistance, BME_GAS_SCALE, BME_GAS_OFFSET, 0.0f, 10000000.0f);
  reading.valid = true;
  return reading;
}

void initializeFirebaseIfNeeded() {
  if (firebaseStarted || WiFi.status() != WL_CONNECTED) {
    return;
  }
  firebaseConfig.api_key = FIREBASE_API_KEY;
  firebaseConfig.database_url = FIREBASE_DATABASE_URL;
  firebaseConfig.token_status_callback = tokenStatusCallback;
  firebaseAuth.user.email = FIREBASE_USER_EMAIL;
  firebaseAuth.user.password = FIREBASE_USER_PASSWORD;
  Firebase.reconnectWiFi(true);
  Firebase.begin(&firebaseConfig, &firebaseAuth);
  firebaseData.setResponseSize(4096);
  firebaseStarted = true;
  Serial.println("[firebase] Client initialized; waiting for authentication token");
}

FirebaseJson readingToJson(const SensorReading &reading) {
  FirebaseJson json;
  json.set("deviceId", reading.deviceId);
  json.set("timestamp", reading.timestamp);
  json.set("mq135", reading.mq135);
  json.set("temperature", reading.temperature);
  json.set("humidity", reading.humidity);
  json.set("pressure", reading.pressure);
  json.set("bme_gas", reading.bmeGas);
  json.set("pir", reading.pirMotion);
  json.set("schemaVersion", 2);
  return json;
}

bool publishReading(const SensorReading &reading) {
  if (!firebaseStarted || !Firebase.ready()) {
    const unsigned long now = millis();
    if (now - lastFirebaseLogAt >= FIREBASE_LOG_INTERVAL_MS) {
      lastFirebaseLogAt = now;
      Serial.println("[firebase] Not ready; retaining latest sample for retry");
    }
    return false;
  }

  FirebaseJson json = readingToJson(reading);
  const String path = String(FIREBASE_SENSOR_ROOT) + "/" + reading.deviceId;
  if (!Firebase.RTDB.pushJSON(&firebaseData, path.c_str(), &json)) {
    Serial.printf("[firebase] Write failed: %s\\n", firebaseData.errorReason().c_str());
    return false;
  }
  Serial.printf("[firebase] Published %s/%s sequence=%lu\\n", path.c_str(),
                firebaseData.pushName().c_str(),
                static_cast<unsigned long>(reading.sequence));
  return true;
}
}  // namespace

void setup() {
  Serial.begin(115200);
  delay(300);
  Serial.println("\\n[boot] AI odor sensor node starting");

  if (!configurationLooksValid()) {
    Serial.println("[boot] Configuration invalid; device will not connect");
  }

  deviceId = buildDeviceId();
  Serial.printf("[boot] Device ID: %s\\n", deviceId.c_str());

  pinMode(PIR_PIN, INPUT);
  initializeBme();

  WiFi.mode(WIFI_STA);
  WiFi.setAutoReconnect(true);
  connectWiFiIfNeeded();
}

void loop() {
  connectWiFiIfNeeded();

  if (WiFi.status() == WL_CONNECTED) {
    configureTimeIfNeeded();
    initializeFirebaseIfNeeded();
  }

  retrySensorsIfNeeded();

  if (hasPendingReading && publishReading(pendingReading)) {
    hasPendingReading = false;
  }

  const unsigned long now = millis();
  if (!hasPendingReading && now - lastSampleAt >= SAMPLE_INTERVAL_MS) {
    lastSampleAt = now;
    SensorReading reading = collectReading();
    if (reading.valid) {
      Serial.printf("[sensor] Sample sequence=%lu error_mask=0x%08lX pir=%s\\n",
                    static_cast<unsigned long>(reading.sequence),
                    static_cast<unsigned long>(reading.errorMask),
                    reading.pirMotion ? "motion" : "clear");
      pendingReading = reading;
      hasPendingReading = true;
      if (publishReading(pendingReading)) {
        hasPendingReading = false;
      }
    }
  }

  delay(10);
}
