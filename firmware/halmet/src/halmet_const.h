#ifndef HALMET_CONST_H_
#define HALMET_CONST_H_

#include <Arduino.h>

namespace sensesp {

// I2C pins on HALMET.
const int kSDAPin = 21;
const int kSCLPin = 22;

// ADS1115 I2C address
const int kADS1115Address = 0x4b;

// CAN bus (NMEA 2000) pins on HALMET
const gpio_num_t kCANRxPin = GPIO_NUM_18;
const gpio_num_t kCANTxPin = GPIO_NUM_19;

// HALMET digital input pins
const int kDigitalInputPin1 = GPIO_NUM_23;
const int kDigitalInputPin2 = GPIO_NUM_25;
const int kDigitalInputPin3 = GPIO_NUM_27;
const int kDigitalInputPin4 = GPIO_NUM_26;

// HALMET 1-Wire header, from the onewire.kicad_sch DQ net traced to the
// ESP32-WROOM-32 IO4 pin (HALMET.kicad_pro rev 1.0.1) -- not silkscreened.
const gpio_num_t kOneWirePin = GPIO_NUM_4;

// TM1637 segmented display, on J201 header pins (raw 3.3 V ESP32 IO, free on
// the schematic): DIO on pin 5, CLK on pin 7, per the enclosure wiring table.
const int kSegmentDioPin = GPIO_NUM_17;
const int kSegmentClkPin = GPIO_NUM_16;
// The second TM1637 shares CLK, 3V3 and GND with the first and has its own DIO,
// on J201 pin 17 (IO13, JTAG TCK: output-capable, not a strapping pin). The first shows RPM, the
// second engine hours.
const int kHoursDioPin = GPIO_NUM_13;

// IR flame module (LM393) DO, on J201 header pin 10. A 3.3 V module inside the
// enclosure needs no isolated D input. GPIO 34 is input-only with no internal
// pull-up: a 10 k pull-up to the header's 3V3 keeps an unplugged module from
// reading as a flame.
const int kFlameSensorPin = GPIO_NUM_34;

// Piezo alarm on J201 header pin 8. It switches a low-side N-FET (100 ohm gate
// resistor, 100 k gate to ground) that sinks the piezo's negative lead off V+.
const int kPiezoPin = GPIO_NUM_32;

}  // namespace sensesp

#endif /* HALMET_CONST_H_ */
