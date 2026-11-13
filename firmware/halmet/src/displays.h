// Vendored from mark-brannan/SensESP-segmented-led-display (src/displays.h).
// Changes: createTm1637Facade keeps the interface on the heap (the module held
// a reference to a stack local); writePatterns() added for raw text like FIrE.
#ifndef DISPLAY_H
#define DISPLAY_H

//#include <chrono>
#include <AceTMI.h>
#include <AceSegment.h>
#include <AceSegmentWriter.h>
#include "temperature.h"

namespace segmented_led_display {

typedef const uint8_t NumDigits_t;
typedef const uint8_t ClkPin_t;
typedef const uint8_t DioPin_t;
typedef const uint8_t StbPin_t;

const uint8_t NUM_DIGITS_4 = 4;
const uint8_t NUM_DIGITS_6 = 6;
const uint8_t NUM_DIGITS_8 = 8;

// delays based on recommendions of ace_segment author;
// should be 'good enough' for SensESP.
const uint8_t TM1637_BIT_DELAY = 100;
const uint8_t TM1638_DELAY_MICROS = 1;

class DisplayFacade {
 public:
   explicit DisplayFacade(ace_segment::LedModule* ledModule);

   void writeSignedDecimal(int value);
   void writePatterns(const uint8_t* patterns, uint8_t n);
   void writeFloat(float value, uint8_t prec = 2);
   void writeTempDegC(float degressK);
   void writeTempDegF(float degressK);
   void writeHourMinute24(String iso8601);
   void writeMinutesSeconds(String iso8601);

   virtual void begin() = 0;
   virtual void flush() = 0;
   void clear();
   void setBrightness(uint8_t brightness);
   uint8_t size();

 protected:
   ace_segment::LedModule* ledModule;
   ace_segment::PatternWriter<ace_segment::LedModule>* patternWriter;
   ace_segment::NumberWriter<ace_segment::LedModule>* numberWriter;
   ace_segment::ClockWriter<ace_segment::LedModule>* clockWriter;
   ace_segment::TemperatureWriter<ace_segment::LedModule>* temperatureWriter;
};

DisplayFacade::DisplayFacade(ace_segment::LedModule* ledModule)
    : ledModule(ledModule),
      patternWriter(new ace_segment::PatternWriter<ace_segment::LedModule>(*ledModule)),
      numberWriter(new ace_segment::NumberWriter<ace_segment::LedModule>(*patternWriter)),
      clockWriter(new ace_segment::ClockWriter<ace_segment::LedModule>(*numberWriter)),
      temperatureWriter(new ace_segment::TemperatureWriter<ace_segment::LedModule>(*numberWriter))
      {}

void DisplayFacade::clear() {
  this->patternWriter->clear();
}

void DisplayFacade::setBrightness(uint8_t brightness) {
  this->ledModule->setBrightness(brightness);
}

uint8_t DisplayFacade::size() {
  return this->ledModule->size();
}
void DisplayFacade::writePatterns(const uint8_t* patterns, uint8_t n) {
  clear();
  patternWriter->writePatterns(patterns, n < size() ? n : size());
  flush();
}

/**
 * Write a 'decimal' (int) value using similar rules as printf.
 * The display size is implicitly used for the print with (right justified),
 * and a negative sign will be prepended for negative values.
 * For example, for a display of size 4: printf("%-4d", value).
 */
void DisplayFacade::writeSignedDecimal(int value) {
  clear();
  numberWriter->writeSignedDecimal(value, size());
  flush();
}

/**
 * Write a value using the same format as the Print class.
 * @note: Undefined behavior for displays with no decimal segment.
 */
void DisplayFacade::writeFloat(float value, uint8_t prec) {
  clear();
  numberWriter->writeFloat(value, prec);
  flush();
}

void DisplayFacade::writeTempDegC(float degreesK) {
    clear();
    temperatureWriter->writeTempDegC(convertDegreesKtoC(degreesK), size());
    flush();
}

void DisplayFacade::writeTempDegF(float degreesK) {
    clear();
    temperatureWriter->writeTempDegF(convertDegreesKtoF(degreesK), size());
    flush();
}

void DisplayFacade::writeHourMinute24(String iso8601) {
  clear();
  //std::chrono::sys_time<std::chrono::seconds> tp;
  //std::istringstream(iso8601) >> std::chrono::parse("%Y-%m-%dT%H:%M:%SZ", tp);
  int year, month, day, hour, minute, second;
  std::sscanf(iso8601.c_str(), "%d-%d-%dT%d:%d:%dZ", &year, &month, &day, &hour, &minute, &second);

  clockWriter->writeHourMinute24(hour, minute);
  flush();
}

void DisplayFacade::writeMinutesSeconds(String iso8601) {
  clear();
  //std::chrono::sys_time<std::chrono::seconds> tp;
  //std::istringstream(iso8601) >> std::chrono::parse("%Y-%m-%dT%H:%M:%SZ", tp);
  int year, month, day, hour, minute, second;
  std::sscanf(iso8601.c_str(), "%d-%d-%dT%d:%d:%dZ", &year, &month, &day, &hour, &minute, &second);

  clockWriter->writeHourMinute24(minute, second);
  flush();
}

template <template<typename, uint8_t> class T_TM163X_MODULE, typename T_TMII, uint8_t T_DIGITS>
class Tm163xFacade : public DisplayFacade {

 protected:
   T_TMII interface;
   T_TM163X_MODULE<T_TMII, T_DIGITS>* ledModule;

 public:
   Tm163xFacade(
       T_TMII interface,
       T_TM163X_MODULE<T_TMII, T_DIGITS>* ledModule)
        : DisplayFacade(ledModule), ledModule(ledModule), interface(interface) {
          this->begin();
          setBrightness(2);
        }

   void begin() override {
       this->interface.begin();
       this->ledModule->begin();
   }

   void flush() override {
       this->ledModule->flush();
   }
};

// We are always using the 'Simple' interface for SensESP
// because the 'Fast' interfaces are specific to AVR processors
// and the performance wouldn't matter for ESP32 anyway.
using Tmi1637Interface = ace_tmi::SimpleTmi1637Interface;
using Tmi1638Interface = ace_tmi::SimpleTmi1638Interface;

template <uint8_t T_DIGITS>
using Tm1637Facade = Tm163xFacade<ace_segment::Tm1637Module, Tmi1637Interface, T_DIGITS>;
template <uint8_t T_DIGITS>
using Tm1638Facade = Tm163xFacade<ace_segment::Tm1638Module, Tmi1638Interface, T_DIGITS>;

template <uint8_t T_DIGITS>
inline Tm1637Facade<T_DIGITS> createTm1637Facade(
  DioPin_t dioPin,
  ClkPin_t clkPin
) {
  auto* interface = new Tmi1637Interface(dioPin, clkPin, TM1637_BIT_DELAY);
  auto ledModule = new ace_segment::Tm1637Module<Tmi1637Interface, T_DIGITS>(*interface);
  return Tm1637Facade<T_DIGITS>(*interface, ledModule);
}

template <uint8_t T_DIGITS>
inline Tm1638Facade<T_DIGITS> createTm1638Facade(
  DioPin_t dioPin,
  ClkPin_t clkPin,
  StbPin_t stbPin
) {
  auto* interface = new Tmi1638Interface(dioPin, clkPin, stbPin, TM1638_DELAY_MICROS);
  auto ledModule = new ace_segment::Tm1638Module<Tmi1638Interface, T_DIGITS>(*interface);
  return Tm1638Facade<T_DIGITS>(*interface, ledModule);
}

};

#endif /* DISPLAY_H */