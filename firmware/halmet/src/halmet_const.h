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

}  // namespace sensesp

#endif /* HALMET_CONST_H_ */
