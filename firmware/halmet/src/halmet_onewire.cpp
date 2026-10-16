#include "halmet_onewire.h"

#include "sensesp/sensors/sensor.h"
#include "sensesp/signalk/signalk_output.h"
#include "sensesp/ui/config_item.h"

namespace halmet {

// Poll interval for reading back the last conversion. Independent of the
// bus-wide conversion interval driven elsewhere.
const unsigned int kOneWireReadDelay = 2000;  // ms

// 0 degC in Kelvin, Signal K's SI unit for temperature paths.
const float kCelsiusToKelvinOffset = 273.15;

sensesp::FloatProducer* ConnectOneWireTemperatureSender(
    DallasTemperature* dallas, uint8_t device_index, const String& name,
    const String& sk_path, bool enable_signalk_output) {
  auto temperature = new sensesp::RepeatSensor<float>(
      kOneWireReadDelay, [dallas, device_index]() {
        return dallas->getTempCByIndex(device_index) + kCelsiusToKelvinOffset;
      });

  if (enable_signalk_output) {
    char config_path[80];
    snprintf(config_path, sizeof(config_path), "/OneWire/%s/SK Path",
             name.c_str());
    char title[80];
    snprintf(title, sizeof(title), "%s Temperature Signal K Path",
             name.c_str());

    auto temperature_sk_output =
        new sensesp::SKOutputFloat(sk_path.c_str(), config_path,
                                   new sensesp::SKMetadata("K", name.c_str()));

    ConfigItem(temperature_sk_output)->set_title(title);

    temperature->connect_to(temperature_sk_output);
  }

  return temperature;
}

}  // namespace halmet
