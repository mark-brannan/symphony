# Testing the DSC / AIS distress chain

**Never press a radio's DSC distress button or activate a SART, MOB beacon or
EPIRB to test.** Everything here injects synthetic traffic over UDP, and needs
`signalk-dsc` and `signalk-ais-distress` on the server under test.

1. Untick Plugin Config → signalk-dsc → "Report received calls to
   DSCWatch.com". Queued reports send later, even from an offline test.
2. Add a UDP NMEA 0183 input if none exists (Settings → Connections → Add,
   type NMEA0183, udp, port 7777), then restart SignalK.
3. Clone the plugin repos; the npm tarballs omit `scripts/`.

   ```bash
   git clone https://github.com/sailingnaturali/signalk-dsc
   git clone https://github.com/sailingnaturali/signalk-ais-distress
   ```

4. Fire traffic; always pass `--host`, the default is the author's boat.

   ```bash
   node signalk-dsc/scripts/send-test-dsc.js --host localhost --port 7777
   node signalk-dsc/scripts/send-test-dsc.js --host localhost --port 7777 --nature mob --category urgency
   node signalk-ais-distress/scripts/send-test-ais.js --host localhost --port 7777 --beacon mob
   ```

5. *Verify* via the API, not the phone; per-call alarms never reach `signalk-ntfy`.

   ```bash
   curl -s -H "Authorization: Bearer $TOK" localhost:3000/signalk/v2/api/resources/dsc-calls
   curl -s -H "Authorization: Bearer $TOK" localhost:3000/signalk/v2/api/resources/ais-distress
   curl -s -H "Authorization: Bearer $TOK" localhost:3000/signalk/v1/api/vessels/self/notifications
   ```

   Expect the call, a `notifications.received.<category>.<id>` each, and
   `notifications.mob` for `--beacon mob`.

6. Clear the alarms with a readwrite token:

   ```bash
   cd signalk-dsc          && SIGNALK_TOKEN=$TOK node scripts/clear-dsc-alarm.js --host localhost --category all
   cd ../signalk-ais-distress && SIGNALK_TOKEN=$TOK node scripts/clear-ais-alarm.js --host localhost --beacon all
   ```

7. Restore DSCWatch reporting and remove the test UDP input.
