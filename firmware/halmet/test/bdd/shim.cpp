// A C face on halmet::Panel for ctypes.

#include <cstring>

#include "alerts.h"

using halmet::Panel;
using halmet::Writes;

extern "C" {

struct CInputs {
  uint32_t up_s;
  float rpm;
  int oil, coolant, alt_fresh;
  float alt_v;
  const char* reset;
  int sk_connected;
  uint32_t largest_block;
  float hours;
};

struct CWrites {
  int segment;
  uint8_t pattern[4];
  int hours_segment;
  uint8_t hours_pattern[4];
  int row6;
  char row6_text[40];
  int row7;
  char row7_text[40];
  int piezo;
};

static void Out(const Writes& w, CWrites* out) {
  std::memset(out, 0, sizeof *out);
  out->segment = w.segment;
  std::memcpy(out->pattern, w.pattern, 4);
  out->hours_segment = w.hours_segment;
  std::memcpy(out->hours_pattern, w.hours_pattern, 4);
  out->row6 = w.row6;
  std::strncpy(out->row6_text, w.row6_text.c_str(), sizeof out->row6_text - 1);
  out->row7 = w.row7;
  std::strncpy(out->row7_text, w.row7_text.c_str(), sizeof out->row7_text - 1);
  out->piezo = w.piezo;
}

void* panel_new() { return new Panel(); }
void panel_free(void* p) { delete static_cast<Panel*>(p); }
int panel_flame_alarm(void* p) { return static_cast<Panel*>(p)->flame_alarm(); }

void panel_seen(void* p, uint32_t now_ms, int seen, CWrites* out) {
  Out(static_cast<Panel*>(p)->Seen(now_ms, seen), out);
}

void panel_flame_tick(void* p, uint32_t now_ms, int seen, uint32_t on_ms, uint32_t off_ms,
                      uint32_t pulses, uint32_t hold_ms, uint32_t clear_ms, CWrites* out) {
  Out(static_cast<Panel*>(p)->FlameTick(now_ms, seen,
                                        {on_ms, off_ms, pulses, hold_ms, clear_ms}),
      out);
}

void panel_second_tick(void* p, const CInputs* in, CWrites* out) {
  Out(static_cast<Panel*>(p)->SecondTick({in->up_s, in->rpm, in->oil != 0, in->coolant != 0,
                                          in->alt_fresh != 0, in->alt_v, in->reset,
                                          in->sk_connected != 0, in->largest_block,
                                          in->hours}),
      out);
}

}  // extern "C"
