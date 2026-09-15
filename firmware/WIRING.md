# ESP32 sensor-node wiring

## Recommended ESP32 DevKit V1 pins

| Device | Signal | ESP32 pin | Notes |
| --- | --- | --- | --- |
| BME688 | VIN | 3.3 V | Use a 3.3 V-compatible breakout |
| BME688 | GND | GND | Common ground |
| BME688 | SDA | GPIO 21 | I2C data |
| BME688 | SCL | GPIO 22 | I2C clock |
| MQ-135 module | AO | GPIO 34 | ADC1 input only |
| MQ-136 module | AO | GPIO 35 | ADC1 input only |
| MQ-3 module | AO | GPIO 32 | ADC1 input only |
| MQ modules | VCC/heater | External regulated 5 V | Size supply for heater current |
| MQ modules | GND | Common GND | Join 5 V supply ground to ESP32 ground |
| GPS module (optional) | TX | GPIO 16 (ESP32 RX2) | 3.3 V logic required |
| GPS module (optional) | RX | GPIO 17 (ESP32 TX2) | Optional if only receiving NMEA |
| GPS module (optional) | GND | GND | Common ground |

## Critical voltage warning

Many MQ breakout boards can output close to 5 V on `AO`. ESP32 ADC pins are not 5 V tolerant. Use a resistor divider or level-conditioning circuit so each ADC input remains at or below 3.3 V. A typical starting divider is 10 kΩ from MQ `AO` to the ESP32 ADC pin and 20 kΩ from the ADC pin to ground; verify the actual module output with a multimeter before connecting it.

Use ADC1 pins only because ESP32 ADC2 conflicts with active Wi-Fi.

## Sensor preparation

- MQ sensors need heater warm-up and burn-in according to their datasheets before calibration.
- Determine clean-air baselines and calibration scale/offset values for each physical module.
- Keep heater current away from the ESP32 3.3 V regulator.
- Place the BME688 where MQ heater heat does not distort temperature/humidity readings.
