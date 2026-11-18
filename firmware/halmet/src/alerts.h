#ifndef __SRC_ALERTS_H__
#define __SRC_ALERTS_H__

// The alert and segment-display logic, free of Arduino so it builds on the
// host: test/bdd runs test/features/alerts.feature against it.

#include <cstdint>
#include <string>

namespace halmet {

struct FlameTiming {
  uint32_t on_ms, off_ms, pulses, hold_ms, clear_ms;
};

struct Inputs {
  uint32_t up_s;
  float rpm;
  bool oil, coolant;
  bool alt_fresh;
  float alt_v;
  const char* reset;  // nullptr: a normal power-on
  bool sk_connected;
  uint32_t largest_block;
  float hours;
};

// What to put on the hardware; anything not flagged stays as it is.
struct Writes {
  bool segment = false;
  uint8_t pattern[4]{};
  bool row6 = false;
  std::string row6_text;
  bool row7 = false;
  std::string row7_text;
  int8_t piezo = -1;  // -1 untouched, 0 off, 1 on
};

// The segment display, OLED rows 6-7 and the piezo, drawn only on a change.
class Panel {
 public:
  // The flame input changed: onset latches the alarm at once.
  Writes Seen(uint32_t now_ms, bool seen);
  // Every 20 ms: the flash burst, the hold and the clearing countdown.
  Writes FlameTick(uint32_t now_ms, bool seen, const FlameTiming& t);
  // Every 1 s: the segment number or alert word, and the alert rows.
  Writes SecondTick(const Inputs& in);
  bool flame_alarm() const { return flame_alarm_; }

 private:
  void OnSeen(uint32_t now_ms, bool seen, Writes& w);
  void DrawFlame(bool lit, const std::string& text, Writes& w);

  bool was_seen_ = false;
  bool flame_alarm_ = false;  // latched: flashing, holding or counting down
  bool flame_clearing_ = false;
  uint32_t flame_since_ms_ = 0;
  uint32_t flame_gone_ms_ = 0;
  bool flame_lit_ = false;
  std::string flame_row_;

  uint32_t tick_ = 0;
  uint8_t shown_[4] = {0xFF, 0xFF, 0xFF, 0xFF};
  uint32_t alt_low_since_ = 0;
  std::string row6_, row7_;
};

}  // namespace halmet

#endif
