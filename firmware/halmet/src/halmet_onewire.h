#ifndef HALMET_ONEWIRE_H_
#define HALMET_ONEWIRE_H_

#include <DallasTemperature.h>

#include "sensesp/system/valueproducer.h"

namespace halmet {

// Reads one DS18B20 by its 1-Wire bus-scan index and publishes it to Signal K
// in Kelvin. Index-based rather than address-based: the chain hasn't been
// benched yet, so per-probe addresses aren't known. Once probes are
// identified on the boat, switch to DallasTemperature::getTempC(DeviceAddress)
// so a probe keeps its Signal K path even if the chain is reordered or a
// probe is added.
//
// dallas must already have begin() called and a periodic
// requestTemperatures() driving conversion; this function only reads back
// the last conversion result.
sensesp::FloatProducer* ConnectOneWireTemperatureSender(
    DallasTemperature* dallas, uint8_t device_index, const String& name,
    const String& sk_path, bool enable_signalk_output = true);

}  // namespace halmet

#endif
