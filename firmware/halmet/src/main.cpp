// Signal K application template file.
//
// This application demonstrates core SensESP concepts in a very
// concise manner. You can build and upload the application as is
// and observe the value changes on the serial port monitor.
//
// You can use this source file as a basis for your own projects.
// Remove the parts that are not relevant to you, and add your own code
// for external hardware libraries.

// Comment out this line to disable NMEA 2000 output.
#define ENABLE_NMEA2000_OUTPUT

// Comment out this line to disable Signal K support. At the moment, disabling
// Signal K support also disables all WiFi functionality.
#define ENABLE_SIGNALK

#include <Adafruit_ADS1X15.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

#include <memory>

#include "counting_nmea2000.h"

#include "n2k_senders.h"
#include "sensesp/net/discovery.h"
#include "sensesp/sensors/analog_input.h"
#include "sensesp/sensors/digital_input.h"
#include "sensesp/sensors/sensor.h"
#include "sensesp/signalk/signalk_output.h"
#include "sensesp/system/lambda_consumer.h"
#include "sensesp/system/system_status_led.h"
#include "sensesp/transforms/lambda_transform.h"
#include "sensesp/transforms/linear.h"
#include "sensesp/ui/config_item.h"
#include "sensesp/ui/status_page_item.h"
#include "sensesp/ui/ui_controls.h"
#ifdef ENABLE_SIGNALK
#include "sensesp_app_builder.h"

// Optional local WiFi seed (gitignored); without it the device opens its setup hotspot.
#if __has_include("wifi_secrets.h")
#include "wifi_secrets.h"
#endif
#define BUILDER_CLASS SensESPAppBuilder
#else
#include "sensesp/net/web/app_command_handler.h"
#include "sensesp/net/web/base_command_handler.h"
#include "sensesp/net/web/config_handler.h"
#include "sensesp/net/web/static_file_handler.h"
#include "sensesp_minimal_app_builder.h"
#define BUILDER_CLASS SensESPMinimalAppBuilder
#endif

#include <DallasTemperature.h>
#include <OneWire.h>

#include "halmet_analog.h"
#include "halmet_const.h"
#include "halmet_digital.h"
#include "halmet_display.h"
#include "halmet_onewire.h"
#include "halmet_serial.h"
#include "displays.h"
#include "engine_hours.h"
#include "sensesp/net/http_server.h"
#include "sensesp/net/networking.h"

using namespace sensesp;
using namespace halmet;

#ifndef ENABLE_SIGNALK
// SensESPMinimalApp creates none of these; the web UI needs them.
std::shared_ptr<SensESPMinimalApp> sensesp_app;
std::shared_ptr<Networking> networking;
std::shared_ptr<MDNSDiscovery> mdns_discovery;
std::shared_ptr<HTTPServer> http_server;
std::shared_ptr<SystemStatusLed> system_status_led;
#endif

/////////////////////////////////////////////////////////////////////
// Declare some global variables required for the firmware operation.

#ifdef ENABLE_NMEA2000_OUTPUT
CountingNMEA2000* nmea2000;
elapsedMillis n2k_time_since_rx = 0;
// Received-message counter shown on the status page.
ObservableValue<int> n2k_rx_counter{0};
#endif

TwoWire* i2c;
Adafruit_SSD1306* display;

// Flame state takes over the segmented display from its RPM/hours/volts pages.
bool flame_active = false;

// Latest values behind the segmented and OLED pages.
uint32_t segment_last_key = UINT32_MAX;  // reset to force a redraw
float last_rpm = 0;
float last_a1_volts = 0;
EngineHours engine_hours;

// Set the ADS1115 GAIN to adjust the analog input voltage range.
// On HALMET, this refers to the voltage range of the ADS1115 input
// AFTER the 33.3/3.3 voltage divider.

// GAIN_TWOTHIRDS: 2/3x gain +/- 6.144V  1 bit = 3mV      0.1875mV (default)
// GAIN_ONE:       1x gain   +/- 4.096V  1 bit = 2mV      0.125mV
// GAIN_TWO:       2x gain   +/- 2.048V  1 bit = 1mV      0.0625mV
// GAIN_FOUR:      4x gain   +/- 1.024V  1 bit = 0.5mV    0.03125mV
// GAIN_EIGHT:     8x gain   +/- 0.512V  1 bit = 0.25mV   0.015625mV
// GAIN_SIXTEEN:   16x gain  +/- 0.256V  1 bit = 0.125mV  0.0078125mV

const adsGain_t kADS1115Gain = GAIN_ONE;

/////////////////////////////////////////////////////////////////////
// Test output pin configuration. If ENABLE_TEST_OUTPUT_PIN is defined,
// GPIO 33 will output a pulse wave at 380 Hz with a 50% duty cycle.
// If this output and GND are connected to one of the digital inputs, it can
// be used to test that the frequency counter functionality is working.
#define ENABLE_TEST_OUTPUT_PIN
#ifdef ENABLE_TEST_OUTPUT_PIN
const int kTestOutputPin = GPIO_NUM_33;
// With the default pulse rate of 100 pulses per revolution (configured in
// halmet_digital.cpp), this frequency corresponds to 3.8 r/s or about 228 rpm.
const int kTestOutputFrequency = 380;
#endif

/////////////////////////////////////////////////////////////////////
// The setup function performs one-time application initialization.
void setup() {
  SetupLogging(ESP_LOG_DEBUG);

  // These calls can be used for fine-grained control over the logging level.
  // esp_log_level_set("*", esp_log_level_t::ESP_LOG_DEBUG);

  Serial.begin(115200);

  /////////////////////////////////////////////////////////////////////
  // Initialize the application framework

  // Construct the global SensESPApp() object
  BUILDER_CLASS builder;
  sensesp_app = (&builder)
                    // EDIT: Set a custom hostname for the app.
                    ->set_hostname("symphony-halmet")
                    // EDIT: Optionally, hard-code the WiFi and Signal K server
                    // settings. This is normally not needed. These three calls
                    // exist only on SensESPAppBuilder and do not compile when
                    // ENABLE_SIGNALK is commented out (SensESPMinimalAppBuilder).
                    //->set_wifi("My WiFi SSID", "my_wifi_password")
                    //->set_sk_server("192.168.10.3", 80)
                    // EDIT: Enable OTA updates with a password.
                    //->enable_ota("my_ota_password")
#ifdef WIFI_SSID
                    ->set_wifi_client(WIFI_SSID, WIFI_PASSWORD)
#endif
                    ->get_app();

#ifndef ENABLE_SIGNALK
  // Initialize components that would normally be present in SensESPApp
  networking = std::make_shared<Networking>("/System/WiFi Settings", "", "");
  mdns_discovery = std::make_shared<MDNSDiscovery>();
  http_server = std::make_shared<HTTPServer>();
  // Nothing drives the LED here; SensESPApp is what connects it to the
  // system status controller.
  system_status_led = std::make_shared<SystemStatusLed>(LED_BUILTIN);
  add_static_file_handlers(http_server);
  add_base_app_http_command_handlers(http_server);
  add_app_http_command_handlers(http_server, networking);
  add_config_handlers(http_server);
#endif

  // initialize the I2C bus
  i2c = new TwoWire(0);
  i2c->begin(kSDAPin, kSCLPin);

  // Initialize ADS1115
  auto ads1115 = new Adafruit_ADS1115();

  ads1115->setGain(kADS1115Gain);
  bool ads_initialized = ads1115->begin(kADS1115Address, i2c);
  debugD("ADS1115 initialized: %d", ads_initialized);

#ifdef ENABLE_TEST_OUTPUT_PIN
  pinMode(kTestOutputPin, OUTPUT);
  // Set the LEDC peripheral to a 13-bit resolution
  ledcAttach(kTestOutputPin, kTestOutputFrequency, 13);
  // Set the duty cycle to 50%
  // Duty cycle value is calculated based on the resolution
  // For 13-bit resolution, max value is 8191, so 50% is 4096
  ledcWrite(kTestOutputPin, 4096);
#endif

#ifdef ENABLE_NMEA2000_OUTPUT
  /////////////////////////////////////////////////////////////////////
  // Initialize NMEA 2000 functionality

  nmea2000 = new CountingNMEA2000(kCANTxPin, kCANRxPin);

  // The send buffer was reduced from this example's earlier 250 frames to 96
  // (about 2.5 KB) to reclaim contiguous heap for the mbedTLS record
  // allocation -- raising it back can reintroduce MBEDTLS_ERR_SSL_ALLOC_FAILED;
  // re-check the largest free block on the status page before doing so. The
  // receive side is not set: NMEA2000_twai uses fixed 40-entry TWAI queues and
  // ignores SetN2kCANReceiveFrameBufSize.
  nmea2000->SetN2kCANSendFrameBufSize(96);

  // Set Product information
  // EDIT: Change the values below to match your device.
  nmea2000->SetProductInformation(
      "20231229",  // Manufacturer's Model serial code (max 32 chars)
      104,         // Manufacturer's product code
      "HALMET",    // Manufacturer's Model ID (max 33 chars)
      "1.0.0",     // Manufacturer's Software version code (max 40 chars)
      "1.0.0"      // Manufacturer's Model version (max 24 chars)
  );

  // For device class/function information, see:
  // http://www.nmea.org/Assets/20120726%20nmea%202000%20class%20&%20function%20codes%20v%202.00.pdf

  // For mfg registration list, see:
  // https://actisense.com/nmea-certified-product-providers/
  // The format is inconvenient, but the manufacturer code below should be
  // one not already on the list.

  // EDIT: Change the class and function values below to match your device.
  nmea2000->SetDeviceInformation(
      GetBoardSerialNumber(),  // Unique number. Use e.g. Serial number.
      140,                     // Device function: Engine
      50,                      // Device class: Propulsion
      2046);                   // Manufacturer code

  nmea2000->SetMode(tNMEA2000::N2km_NodeOnly,
                    71  // Default N2k node address
  );
  nmea2000->EnableForward(false);

  // Count received N2K messages and feed the watchdog.
  nmea2000->SetMsgHandler([](const tN2kMsg&) {
    n2k_rx_counter.set(n2k_rx_counter.get() + 1);
    n2k_time_since_rx = 0;
  });

  nmea2000->Open();

  // No need to parse the messages at every single loop iteration; 1 ms will do
  event_loop()->onRepeat(1, []() { nmea2000->ParseMessages(); });

  // NMEA 2000 message counters on the status page. TX is tallied by
  // CountingNMEA2000 on each accepted SendMsg; RX by the handler above.
  // connect_to() copies these shared_ptrs into the producer's observer list, so
  // they keep themselves alive.
  auto n2k_rx_status = std::make_shared<StatusPageItem<int>>(
      "NMEA 2000 Received Messages", 0, "NMEA 2000", 300);
  n2k_rx_counter.connect_to(n2k_rx_status);
  auto n2k_tx_status = std::make_shared<StatusPageItem<int>>(
      "NMEA 2000 Transmitted Messages", 0, "NMEA 2000", 310);
  nmea2000->tx_count_.connect_to(n2k_tx_status);
#endif  // ENABLE_NMEA2000_OUTPUT

  // Initialize the OLED display
  bool display_present = InitializeSSD1306(sensesp_app->get(), &display, i2c);

  ///////////////////////////////////////////////////////////////////
  // Analog inputs

#ifdef ENABLE_SIGNALK
  bool enable_signalk_output = true;
#else
  bool enable_signalk_output = false;
#endif

  // A1-A4 voltages. A1 and A2 take their planned paths; A3 and A4 are raw
  // bench points until the ignition sense and A4 transducer are fitted.
  struct AnalogPoint {
    int channel;
    const char* config_path;
    const char* title;
    const char* sk_path;
  };
  const AnalogPoint analog_points[] = {
      {0, "/Voltage A1", "A1", "electrical.batteries.start.voltage"},
      {1, "/Voltage A2", "A2", "propulsion.main.alternatorVoltage"},
      {2, "/Voltage A3", "A3", "sensors.a3.voltage"},
      {3, "/Voltage A4", "A4", "sensors.a4.voltage"},
  };
  for (const auto& p : analog_points) {
    auto voltage = new ADS1115VoltageInput(ads1115, p.channel, p.config_path);
    ConfigItem(voltage)
        ->set_title((String("Analog Voltage ") + p.title).c_str())
        ->set_description((String("Voltage level of analog input ") + p.title).c_str())
        ->set_sort_order(3000 + p.channel);
#ifdef ENABLE_SIGNALK
    voltage->connect_to(new SKOutputFloat(
        p.sk_path, p.config_path + String(" SK Path"),
        new SKMetadata("V", (String("Analog Voltage ") + p.title).c_str())));
#endif
    if (p.channel == 0) {
      voltage->connect_to(new LambdaConsumer<float>(
          [](float value) { last_a1_volts = value; }));
    }
  }

  ///////////////////////////////////////////////////////////////////
  // 1-Wire temperature inputs (DS18B20 chain)

  auto one_wire = new OneWire(kOneWirePin);
  auto dallas_temperature = new DallasTemperature(one_wire);
  dallas_temperature->begin();
  dallas_temperature->setWaitForConversion(false);

  // One periodic request drives conversion for every probe on the bus; each
  // sender below just reads back the last conversion, by bus-scan index.
  event_loop()->onRepeat(
      2000, [dallas_temperature]() { dallas_temperature->requestTemperatures(); });

  // EDIT: default point set from the plan, addressed by bus-scan index --
  // switch to DallasTemperature::getTempC(DeviceAddress) once the chain is
  // benched and each probe's physical position is known. Raw-water has no
  // settled Signal K path; this one is a guess, change it when a better
  // convention turns up.
  auto coolant_temperature = ConnectOneWireTemperatureSender(
      dallas_temperature, 0, "Coolant", "propulsion.main.coolantTemperature",
      enable_signalk_output);
  auto exhaust_temperature = ConnectOneWireTemperatureSender(
      dallas_temperature, 1, "Exhaust", "propulsion.main.exhaustTemperature",
      enable_signalk_output);
  auto alternator_temperature = ConnectOneWireTemperatureSender(
      dallas_temperature, 2, "Alternator",
      "electrical.alternators.main.temperature", enable_signalk_output);
  auto raw_water_temperature = ConnectOneWireTemperatureSender(
      dallas_temperature, 3, "Raw Water Intake",
      "propulsion.main.rawWaterTemperature", enable_signalk_output);
  auto engine_room_temperature = ConnectOneWireTemperatureSender(
      dallas_temperature, 4, "Engine Room",
      "environment.inside.engineRoom.temperature", enable_signalk_output);

  ///////////////////////////////////////////////////////////////////
  // Digital alarm inputs

  // EDIT: More alarm inputs can be defined by duplicating the lines below.
  // Make sure to not define a pin for both a tacho and an alarm.
  auto alarm_d2_input = ConnectAlarmSender(kDigitalInputPin2, "oil-pressure",
                                           enable_signalk_output);
  auto alarm_d3_input = ConnectAlarmSender(kDigitalInputPin3, "coolant-temp",
                                           enable_signalk_output);
  // Segmented TM1637 display: RPM normally, FIrE while a flame is seen.
  static auto segment_display =
      segmented_led_display::createTm1637Facade<segmented_led_display::NUM_DIGITS_4>(
          kSegmentDioPin, kSegmentClkPin);
  segment_display.writeSignedDecimal(0);

  // IR flame module on D4. The module output is active-low, but how that
  // reaches the isolated D input is unmeasured, so polarity is a setting.
  auto* flame_active_low = new CheckboxConfig(
      true, "Flame input active-low", "/Alarm flame/Active Low");
  ConfigItem(flame_active_low)
      ->set_title("Flame input active-low")
      ->set_description("Flame detected when D4 reads low. Restart to apply.")
      ->set_sort_order(3020)
      ->set_requires_restart(true);
  const bool flame_low = flame_active_low->get_value();

  auto* flame_input = new DigitalInputState(kDigitalInputPin4, INPUT, 100);
  auto* flame_detected = flame_input->connect_to(
      new LambdaTransform<bool, bool>(
          [flame_low](bool pin) { return flame_low ? !pin : pin; }));
  // Sampled every 100 ms; redraw only on a change, both displays block the loop.
  flame_detected->connect_to(new LambdaConsumer<bool>([](bool detected) {
    if (detected == flame_active) return;
    flame_active = detected;
    segment_last_key = UINT32_MAX;
    if (detected) {
      // F, I, r, E
      static const uint8_t kFire[4] = {0x71, 0x06, 0x50, 0x79};
      segment_display.writePatterns(kFire, 4);
    }
  }));
  if (enable_signalk_output) {
    auto* flame_sk = new SKOutputBool("alarm.flame", "/Alarm flame/SK Path");
    ConfigItem(flame_sk)->set_title("Alarm flame Signal K Path");
    flame_detected->connect_to(flame_sk);
  }

  // In this example, alarm_d3_input is active low, so invert the value.
  auto alarm_d3_inverted = alarm_d3_input->connect_to(
      new LambdaTransform<bool, bool>([](bool value) { return !value; }));

#ifdef ENABLE_NMEA2000_OUTPUT
  // EDIT: This example connects the D2 alarm input to the low oil pressure
  // warning. Modify according to your needs.
  N2kEngineParameterDynamicSender* engine_dynamic_sender =
      new N2kEngineParameterDynamicSender("/NMEA 2000/Engine 1 Dynamic", 0,
                                          nmea2000);

  ConfigItem(engine_dynamic_sender)
      ->set_title("Engine 1 Dynamic")
      ->set_description("NMEA 2000 dynamic engine parameters for engine 1")
      ->set_sort_order(3010);

  alarm_d2_input->connect_to(engine_dynamic_sender->low_oil_pressure_);

  // This is just an example -- normally temperature alarms would not be
  // active-low (inverted).
  alarm_d3_inverted->connect_to(engine_dynamic_sender->over_temperature_);
#endif  // ENABLE_NMEA2000_OUTPUT

  // FIXME: Transmit the alarms over SK as well.

  ///////////////////////////////////////////////////////////////////
  // Digital tacho inputs

  // Connect the tacho senders. Engine name is "main".
  // EDIT: More tacho inputs can be defined by duplicating the line below.
  auto tacho_d1_frequency =
      ConnectTachoSender(kDigitalInputPin1, "main", enable_signalk_output);

#ifdef ENABLE_NMEA2000_OUTPUT
  // Connect outputs to the N2k senders.
  // EDIT: Make sure this matches your tacho configuration above.
  //       Duplicate the lines below to connect more tachos, but be sure to
  //       use different engine instances.
  N2kEngineParameterRapidSender* engine_rapid_sender =
      new N2kEngineParameterRapidSender("/NMEA 2000/Engine 1 Rapid Update", 0,
                                        nmea2000);  // Engine 1, instance 0

  ConfigItem(engine_rapid_sender)
      ->set_title("Engine 1 Rapid Update")
      ->set_description("NMEA 2000 rapid update engine parameters for engine 1")
      ->set_sort_order(3015);

  tacho_d1_frequency->connect_to(&(engine_rapid_sender->engine_speed_));
#endif  // ENABLE_NMEA2000_OUTPUT

  tacho_d1_frequency->connect_to(
      new LambdaConsumer<float>([](float value) { last_rpm = 60 * value; }));

  engine_hours.begin();
  event_loop()->onRepeat(1000, []() { engine_hours.tick(last_rpm); });
#ifdef ENABLE_SIGNALK
  // Signal K run time is in seconds.
  auto* run_time = new RepeatSensor<float>(
      10000, []() { return static_cast<float>(engine_hours.seconds()); });
  run_time->connect_to(new SKOutputFloat(
      "propulsion.main.runTime", "/Engine Hours/SK Path",
      new SKMetadata("s", "Engine run time")));
#endif

#ifdef ENABLE_NMEA2000_OUTPUT
  ///////////////////////////////////////////////////////////////////
  // Configure the NMEA 2000 watchdog

  CheckboxConfig* enable_n2k_watchdog_config = new CheckboxConfig(
      false, "Enable NMEA 2000 Watchdog", "/NMEA 2000/Enable Watchdog");

  ConfigItem(enable_n2k_watchdog_config)
      ->set_title("Enable NMEA 2000 Watchdog")
      ->set_description(
          "Enable the NMEA 2000 watchdog. If enabled, the device will reboot "
          "after two minutes if no NMEA 2000 messages are received. This "
          "setting requires a restart to take effect.")
      ->set_sort_order(100)
      ->set_requires_restart(true);

  if (enable_n2k_watchdog_config->get_value()) {
    event_loop()->onRepeat(1000, []() {
      if (n2k_time_since_rx > 120000) {
        ESP_LOGE("NMEA2000", "No messages received in 2 minutes. Restarting.");
        // All hope is lost; it doesn't matter if we delay for a bit to ensure
        // the log message is sent.
        delay(10);
        ESP.restart();
      }
    });
  }
#endif  // ENABLE_NMEA2000_OUTPUT

  ///////////////////////////////////////////////////////////////////
  // Display setup

  // OLED: rows 0-5 are host, IP, uptime, engine hours, RPM, A1 volts.
  if (display_present) {
    event_loop()->onRepeat(1000, []() {
      PrintValue(display, 1, "IP:", WiFi.localIP().toString());
      uint32_t up = millis() / 1000;
      char buf[24];
      snprintf(buf, sizeof(buf), "%ud %02u:%02u:%02u", (unsigned)(up / 86400),
               (unsigned)(up / 3600 % 24), (unsigned)(up / 60 % 60),
               (unsigned)(up % 60));
      PrintValue(display, 2, "Up", String(buf));
      PrintValue(display, 3, "Hours", engine_hours.hours());
      PrintValue(display, 4, "RPM", last_rpm);
      PrintValue(display, 5, "Batt V", last_a1_volts);
    });
  }

  // Segmented display cycles RPM, engine hours, battery volts: a 1 s label
  // then 3 s of value, so 12.6 h and 12.6 V can't be confused. Only redraws on
  // a change because the TM1637 write blocks the loop.
  event_loop()->onRepeat(1000, []() {
    if (flame_active) return;
    static uint32_t tick = 0;
    const uint32_t page = (tick / 4) % 3, step = tick % 4;
    tick++;
    int rpm = (int)last_rpm;
    int hours_x10 = (int)(engine_hours.hours() * 10);
    int volts_x10 = (int)(last_a1_volts * 10);
    uint32_t key = page * 4 + step;
    if (step > 0) key = (key << 20) | (page == 0 ? rpm : page == 1 ? hours_x10 : volts_x10);
    if (key == segment_last_key) return;
    segment_last_key = key;
    // 7-segment glyphs: rPn, Hrs, bAtt
    static const uint8_t kLabels[3][4] = {{0x50, 0x73, 0x54, 0x00},
                                          {0x76, 0x50, 0x6D, 0x00},
                                          {0x7C, 0x77, 0x78, 0x78}};
    if (step == 0) {
      segment_display.writePatterns(kLabels[page], 4);
    } else if (page == 0) {
      segment_display.writeSignedDecimal(rpm);
    } else if (page == 1) {
      if (hours_x10 < 10000) segment_display.writeFloat(hours_x10 / 10.0f, 1);
      else segment_display.writeSignedDecimal(hours_x10 / 10);
    } else {
      segment_display.writeFloat(volts_x10 / 10.0f, 1);
    }
  });

  // Heap and main-loop-stack diagnostics on the status page. The largest free
  // block is what the TLS handshake needs as one contiguous allocation.
  auto largest_block_status = std::make_shared<StatusPageItem<int>>(
      "Largest free block (bytes)", 0, "System", 250);
  event_loop()->onRepeat(2000, [largest_block_status]() {
    largest_block_status->set(static_cast<int>(ESP.getMaxAllocHeap()));
  });

  auto main_loop_stack_status = std::make_shared<StatusPageItem<int>>(
      "Main loop min free stack (bytes)", 0, "System", 260);
  event_loop()->onRepeat(2000, [main_loop_stack_status]() {
    main_loop_stack_status->set(
        static_cast<int>(uxTaskGetStackHighWaterMark(nullptr)));
  });

  // To avoid garbage collecting all shared pointers created in setup(),
  // loop from here.
  while (true) {
    loop();
  }
}

void loop() { event_loop()->tick(); }
