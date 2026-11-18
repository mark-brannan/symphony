#include "alerts.h"

#include <cstring>

namespace halmet {

namespace {
// F, I, r, E
const uint8_t kFire[4] = {0x71, 0x06, 0x50, 0x79};
const uint8_t kBlank[4] = {0, 0, 0, 0};
const uint8_t kHot[4] = {0x00, 0x76, 0x5C, 0x78};
const uint8_t kErr[4] = {0x00, 0x79, 0x50, 0x50};
const uint8_t kDigit[10] = {0x3F, 0x06, 0x5B, 0x4F, 0x66,
                            0x6D, 0x7D, 0x07, 0x7F, 0x6F};
}  // namespace

void Panel::DrawFlame(bool lit, const std::string& text, Writes& w) {
  if (lit != flame_lit_) {
    flame_lit_ = lit;
    w.segment = true;
    std::memcpy(w.pattern, lit ? kFire : kBlank, 4);
  }
  if (text != flame_row_) {
    flame_row_ = text;
    w.row6 = true;
    w.row6_text = text;
  }
}

// Onset lights both displays and the piezo at once, and restarts an alarm
// that is counting down.
void Panel::OnSeen(uint32_t now_ms, bool seen, Writes& w) {
  if (seen == was_seen_) return;
  was_seen_ = seen;
  if (seen && (!flame_alarm_ || flame_clearing_)) {
    flame_alarm_ = true;
    flame_clearing_ = false;
    flame_since_ms_ = now_ms;
    DrawFlame(true, "FLAME DETECTED", w);
    w.piezo = 1;
  }
}

Writes Panel::Seen(uint32_t now_ms, bool seen) {
  Writes w;
  OnSeen(now_ms, seen, w);
  return w;
}

// A burst of flashes and beeps, then steady, repeated while the flame is
// seen. Flame gone and burst done: steady, "FLAME clearing Ns" counting down,
// then blank.
Writes Panel::FlameTick(uint32_t now, bool seen, const FlameTiming& t) {
  Writes w;
  OnSeen(now, seen, w);
  if (!flame_alarm_) return w;
  if (!flame_clearing_) {
    const uint32_t period = t.on_ms + t.off_ms;
    const uint32_t burst = period * t.pulses;
    const uint32_t at = (now - flame_since_ms_) % (burst + t.hold_ms);
    const bool in_burst = at < burst;
    if (in_burst || seen) {
      const bool lit = !in_burst || at % period < t.on_ms;
      DrawFlame(lit, lit ? "FLAME DETECTED" : "", w);
      w.piezo = in_burst && lit;
      return w;
    }
    flame_clearing_ = true;
    flame_gone_ms_ = now;
    w.piezo = 0;
  }
  const uint32_t gone = now - flame_gone_ms_;
  if (gone >= t.clear_ms) {
    flame_alarm_ = false;
    flame_clearing_ = false;
    DrawFlame(false, "", w);
  } else {
    const uint32_t left_s = (t.clear_ms - gone + 999) / 1000;
    DrawFlame(true, "FLAME clearing " + std::to_string(left_s) + "s", w);
  }
  return w;
}

Writes Panel::SecondTick(const Inputs& in) {
  Writes w;
  tick_++;
  const uint32_t up = in.up_s;

  // Most serious first, 2 s each, with a k/n counter when there are several.
  std::string alerts[6];
  int n = 0;
  if (in.oil) alerts[n++] = "LOW OIL PRESSURE";
  if (in.coolant) alerts[n++] = "COOLANT HOT";
  // Alternator under 13.0 V for 30 s with the engine turning.
  const bool alt_low = in.rpm > 0 && in.alt_fresh && in.alt_v < 13.0f;
  if (!alt_low) alt_low_since_ = 0;
  else if (alt_low_since_ == 0) alt_low_since_ = up ? up : 1;
  const bool alt_alert = alt_low_since_ && up - alt_low_since_ >= 30;
  if (alt_alert) alerts[n++] = "Alt not charging";
  if (in.reset && up < 600) alerts[n++] = std::string("Reset: ") + in.reset;
  const bool sk_down = !in.sk_connected && up > 60;
  if (sk_down) alerts[n++] = "No Signal K link";
  const bool low_memory = in.largest_block < 30000;
  if (low_memory) alerts[n++] = "Low memory";
  // An engine alert the segment has no word of its own for.
  const bool err_alert = in.oil || alt_alert || sk_down || low_memory;

  // Segment: RPM while the engine turns, whole hours while stopped. One second
  // in every four goes to an alert: Hot for the coolant alarm, Err for any
  // other but a reset; both on, they take turns. The flame owns it outright.
  if (flame_alarm_) {
    shown_[0] = 0xFF;  // forces a redraw after it clears
  } else {
    uint8_t next[4] = {0, 0, 0, 0};
    if (in.coolant && tick_ % 4 == 0) {
      std::memcpy(next, kHot, 4);
    } else if (err_alert && tick_ % 4 == (in.coolant ? 2u : 0u)) {
      std::memcpy(next, kErr, 4);
    } else {
      int v = in.rpm > 0 ? (int)in.rpm : (int)in.hours;
      v = v < 0 ? 0 : v > 9999 ? 9999 : v;
      for (int i = 3, d = 0; i >= 0; i--, d++) {
        if (v > 0 || d == 0) next[i] = kDigit[v % 10];
        v /= 10;
      }
    }
    if (std::memcmp(next, shown_, 4) != 0) {
      std::memcpy(shown_, next, 4);
      w.segment = true;
      std::memcpy(w.pattern, shown_, 4);
    }
  }

  // Row 6 carries the alerts, the flame's while latched; row 7 the alerts then.
  std::string alert_text;
  if (n > 0) {
    const int k = (tick_ / 2) % n;
    alert_text = alerts[k];
    if (n > 1) alert_text += " " + std::to_string(k + 1) + "/" + std::to_string(n);
  }
  const std::string want6 = flame_alarm_ ? row6_ : alert_text;
  const std::string want7 = flame_alarm_ ? alert_text : "";
  if (!flame_alarm_ && want6 != row6_) {
    row6_ = want6;
    w.row6 = true;
    w.row6_text = row6_;
  }
  if (want7 != row7_) {
    row7_ = want7;
    w.row7 = true;
    w.row7_text = row7_;
  }
  if (flame_alarm_) row6_ = "\x01";  // the flasher owns row 6; redraw after it clears
  return w;
}

}  // namespace halmet
