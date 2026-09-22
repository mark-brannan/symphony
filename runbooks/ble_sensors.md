# Adding a BLE sensor

In `signalk/plugin-config-data/bt-sensors-plugin-sk.json`, per peripheral.
`params.pollFreq` and an explicit `paths` block are both required; without
either the sensor connects and publishes nothing, with no error anywhere.
Saving through the plugin's config UI writes both.

```json
{
  "active": true,
  "mac_address": "A5:C2:37:40:01:46",
  "params": { "name": "House Battery 1", "sensorClass": "JBDBMS", "batteryID": "0146", "pollFreq": 60 },
  "paths": {
    "voltage": "electrical.batteries.0146.voltage",
    "SOC": "electrical.batteries.0146.capacity.stateOfCharge",
    "temp0": "electrical.batteries.0146.temperature"
  }
}
```

Identify by MAC, not name; both house batteries advertise as `DP04S007L4S200A`.

*Verify* with the `$source` census in
[RUNBOOK.md](../RUNBOOK.md#ble-sensors-silent-after-a-reboot). If no sensor
from the plugin appears at all, it is config, not radio.
