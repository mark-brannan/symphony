#ifndef __SRC_ENGINE_HOURS_H__
#define __SRC_ENGINE_HOURS_H__

#include <Preferences.h>

namespace halmet {

// Engine run time, accumulated while RPM is above a floor and kept in NVS so
// it survives power loss. Stored in whole seconds.
class EngineHours {
 public:
  // Below this the pickup is noise or a coasting flywheel, not a running engine.
  static constexpr float kRunningRpm = 100;
  // Flash write interval; a power cut loses at most this much run time.
  static constexpr uint32_t kSaveIntervalS = 60;

  void begin() {
    prefs_.begin("engine", false);
    seconds_ = prefs_.getULong("run_s", 0);
  }

  // Call once a second with the current RPM.
  void tick(float rpm) {
    if (rpm < kRunningRpm) return;
    seconds_++;
    if (seconds_ % kSaveIntervalS == 0) prefs_.putULong("run_s", seconds_);
  }

  uint32_t seconds() const { return seconds_; }
  float hours() const { return seconds_ / 3600.0f; }

 private:
  Preferences prefs_;
  uint32_t seconds_ = 0;
};

}  // namespace halmet

#endif
