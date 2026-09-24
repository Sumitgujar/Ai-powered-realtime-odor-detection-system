# ESP8266 NodeMCU wiring

This table targets a NodeMCU 1.0-style ESP8266 board using the PlatformIO `nodemcuv2` environment. Confirm the labels and schematic of the exact board before wiring.

## Final pin table

| Device | Signal | NodeMCU label | ESP8266 GPIO | Notes |
| --- | --- | --- | ---: | --- |
| MQ135 module | AO | A0 | ADC/TOUT | Analog input; verify the board-specific voltage range first |
| MQ135 module | VCC/heater | External regulated supply | — | Use the module datasheet voltage/current requirements |
| MQ135 module | GND | GND | — | Common ground with NodeMCU |
| BME680/BME68x | VIN | 3V3 | — | Use a breakout compatible with 3.3 V logic |
| BME680/BME68x | GND | GND | — | Common ground |
| BME680/BME68x | SDA | D2 | GPIO4 | I2C SDA |
| BME680/BME68x | SCL | D1 | GPIO5 | I2C SCL |
| PIR module | OUT | D5 | GPIO14 | Configured as `INPUT`; active-high by default |
| PIR module | VCC | Board/module supply | — | Confirm the PIR output is safe for 3.3 V GPIO |
| PIR module | GND | GND | — | Common ground |

MQ136, MQ3, and GPS wiring are intentionally absent from the migrated firmware.

## A0 safety check — required before direct wiring

Espressif specifies the ESP8266 chip ADC/TOUT input as 0–1.0 V. Some NodeMCU boards add an onboard resistor divider and expose a wider A0 range, but this is not universal across boards and revisions.

Before connecting MQ135 AO:

1. Read the exact board schematic or product documentation.
2. Determine whether A0 is a bare 0–1.0 V ADC input or a divided board-level input.
3. Measure MQ135 AO with a multimeter during warm-up and expected maximum exposure.
4. Add a resistor divider/level shifter if AO can exceed the verified A0 limit.
5. Keep the ADC input within the verified safe range under all conditions.

Do not use the earlier ESP32 0–4095/3.3 V assumptions for this board.

## BME680/BME68x identification

The firmware probes I2C addresses `0x76` and `0x77` using the Adafruit BME680 library. Confirm:

- The breakout is actually BME680 or a compatible BME68x part.
- The breakout voltage regulator/level shifter is appropriate for 3.3 V.
- The address-selection solder bridge matches `0x76` or `0x77`.
- The breakout exposes the gas sensor if `bme_gas` is required.

BME688 hardware may provide additional gas-scanner capabilities that this basic driver does not use. Do not treat a BME688 and BME680 as identical for advanced gas classification.

## PIR considerations

D5/GPIO14 is used because it is separate from the I2C pins and is not one of the ESP8266 boot-strap pins. Confirm the PIR module's output is 3.3 V-safe. If the module produces 5 V logic, use level conditioning before D5.

Allow the PIR module to complete its warm-up period before interpreting motion values. `pir` is stored in Firebase. The schema-v2 ML pipeline excludes PIR from odor features by default unless a trained artifact explicitly opts into it.

## MQ135 calibration

MQ sensors require heater warm-up and module-specific calibration. The firmware reports the averaged raw ADC count after applying:

```text
calibrated_value = raw_adc_count * MQ135_SCALE + MQ135_OFFSET
```

These values are not ppm. Calibrate against known reference conditions and keep the MQ135 heater on an appropriate external supply; do not rely on the NodeMCU 3.3 V regulator for the heater.
