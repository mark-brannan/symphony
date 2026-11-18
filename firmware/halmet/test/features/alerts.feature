Feature: HALMET alerts on the segment display and the OLED
  The 4-digit segment display is for reading at a glance: a number most of the
  time, one word for an alert. The OLED names every alert. Time is in whole
  seconds of the display's 1 s tick; "uptime" is seconds since boot.

  Scenarios tagged @pending describe behaviour the firmware does not have yet.

  Background:
    Given the board has been up for 15 minutes, unless a scenario says otherwise
    And no flame is seen

  # ---------------------------------------------------------------- happy path

  Scenario: Engine running, nothing wrong
    Given the engine is turning at 850 RPM
    And Signal K is connected
    When I watch the displays for 8 seconds
    Then the segment display shows " 850" every second
    And OLED row 6 is blank
    And OLED row 7 is blank

  Scenario: Engine stopped, nothing wrong
    Given the engine is stopped
    And engine hours are 412.7
    And Signal K is connected
    When I watch the displays for 8 seconds
    Then the segment display shows " 412" every second
    And OLED row 6 is blank

  Scenario: RPM and hours never share the screen
    Given engine hours are 412.7
    When the engine goes from stopped to 850 RPM
    Then the segment display changes from " 412" to " 850"
    And it never shows " 412" while RPM is above 0

  # ------------------------------------------------- one condition at a time

  Scenario: Only the Signal K link is down
    Given the engine is turning at 850 RPM
    And Signal K is not connected
    When I watch the displays for 8 seconds
    Then OLED row 6 shows "No Signal K link"
    And it carries no counter
    And the segment display shows " Err" for 1 second in every 4
    And " 850" the other 3 seconds

  Scenario: Signal K down in the first minute after boot is not an alert
    Given the board has been up for 30 seconds
    And Signal K is not connected
    Then OLED row 6 does not show "No Signal K link"
    And the segment display never shows " Err"

  Scenario: Signal K down, engine stopped, hours from the flash cache
    Given the engine is stopped
    And Signal K has not connected since boot
    And the flash cache holds 412.7 engine hours
    Then the segment display shows " 412"

  Scenario: Only the coolant alarm
    Given the engine is turning at 850 RPM
    And the coolant alarm is on
    When I watch the displays for 8 seconds
    Then the segment display shows " Hot" for 1 second in every 4
    And " 850" the other 3 seconds
    And OLED row 6 shows "COOLANT HOT"

  Scenario Outline: One engine alert the segment has no word for
    Given the engine is turning at 850 RPM
    And <condition>
    When I watch the displays for 8 seconds
    Then the segment display shows " Err" for 1 second in every 4
    And OLED row 6 shows "<oled>"

    Examples:
      | condition                                         | oled             |
      | the oil pressure alarm is on                      | LOW OIL PRESSURE |
      | the alternator has read 12.6 V for 30 seconds     | Alt not charging |
      | the largest free heap block is under 30000 bytes  | Low memory       |
      | Signal K is not connected                         | No Signal K link |

  Scenario: A reset reason stays on the OLED
    Given the engine is turning at 850 RPM
    And the board reset 2 minutes ago after a brownout
    Then OLED row 6 shows "Reset: brownout"
    And the segment display never shows " Err" or " Hot"

  # ------------------------------------------------------------ the alternator

  Scenario: Low alternator voltage under 30 seconds is not yet an alert
    Given the engine is turning at 850 RPM
    And the alternator has read 12.6 V for 20 seconds
    Then OLED row 6 does not show "Alt not charging"

  Scenario: Low alternator voltage with the engine stopped is not an alert
    Given the engine is stopped
    And the alternator has read 12.6 V for 5 minutes
    Then OLED row 6 does not show "Alt not charging"

  Scenario: Alternator recovers
    Given "Alt not charging" is showing
    When the alternator reads 14.2 V
    Then "Alt not charging" is gone within 1 second
    And the 30 second wait starts again from zero the next time it drops

  Scenario: No alternator reading
    Given the engine is turning at 850 RPM
    And no alternator voltage has arrived for 10 seconds
    Then OLED row 6 does not show "Alt not charging"

  # ------------------------------------------------------ several at once

  Scenario: Coolant and another engine alert take turns on the segment display
    Given the engine is turning at 850 RPM
    And the coolant alarm is on
    And the oil pressure alarm is on
    When I watch the displays for 8 seconds
    Then each 4 second cycle shows " Hot", " 850", " Err", " 850"

  Scenario: Several engine alerts share one Err
    Given the engine is turning at 850 RPM
    And the oil pressure alarm is on
    And "Alt not charging" is showing
    And the largest free heap block is under 30000 bytes
    Then the segment display shows " Err" for 1 second in every 4
    And never more often

  Scenario: Several alerts cycle on the OLED, most serious first
    Given the oil pressure alarm is on
    And the coolant alarm is on
    And Signal K is not connected
    When I watch OLED row 6 for 6 seconds
    Then it shows, 2 seconds each:
      | LOW OIL PRESSURE 1/3 |
      | COOLANT HOT 2/3      |
      | No Signal K link 3/3 |

  Scenario: Everything at once
    Given the board reset 2 minutes ago after a brownout
    And the oil pressure alarm is on
    And the coolant alarm is on
    And "Alt not charging" is showing
    And Signal K is not connected
    And the largest free heap block is under 30000 bytes
    When I watch OLED row 6 for 12 seconds
    Then it shows, 2 seconds each:
      | LOW OIL PRESSURE 1/6 |
      | COOLANT HOT 2/6      |
      | Alt not charging 3/6 |
      | Reset: brownout 4/6  |
      | No Signal K link 5/6 |
      | Low memory 6/6       |
    And the segment display alternates " Hot" and " Err" in its alert second

  Scenario: An alert clears mid-cycle
    Given OLED row 6 is cycling "LOW OIL PRESSURE 1/2" and "No Signal K link 2/2"
    When Signal K connects
    Then OLED row 6 shows "LOW OIL PRESSURE" with no counter within 2 seconds

  # ------------------------------------------------- several hot readings

  @pending
  Scenario Outline: One hot probe
    Given the <probe> probe reads above its hot threshold
    Then the segment display shows " Hot" for 1 second in every 4
    And OLED row 6 shows "<oled>"

    Examples:
      | probe       | oled             |
      | coolant     | COOLANT HOT      |
      | exhaust     | EXHAUST HOT      |
      | alternator  | ALTERNATOR HOT   |
      | raw water   | RAW WATER HOT    |
      | engine room | ENGINE ROOM HOT  |

  @pending
  Scenario: Several hot probes share one Hot on the segment display
    Given the coolant probe reads above its hot threshold
    And the exhaust probe reads above its hot threshold
    Then the segment display shows " Hot" for 1 second in every 4
    And never more often
    And OLED row 6 cycles "COOLANT HOT 1/2" and "EXHAUST HOT 2/2"

  @pending
  Scenario: The coolant switch and the coolant probe are one alert
    Given the coolant alarm is on
    And the coolant probe reads above its hot threshold
    Then OLED row 6 shows "COOLANT HOT" once in its cycle

  @pending
  Scenario: A stale probe is not hot
    Given the exhaust probe last read above its hot threshold 15 seconds ago
    And nothing has arrived from it since
    Then OLED row 6 does not show "EXHAUST HOT"

  # ----------------------------------------------------------------- flame

  Scenario: Flame owns the segment display and OLED row 6
    Given the oil pressure alarm is on
    And Signal K is not connected
    When a flame is seen
    Then the segment display flashes "FIrE"
    And OLED row 6 flashes "FLAME DETECTED"
    And the piezo sounds with each flash
    And the piezo is silent during the steady hold
    And OLED row 7 cycles "LOW OIL PRESSURE 1/2" and "No Signal K link 2/2"
    And the segment display never shows " Err" while the alarm is latched

  Scenario: After the flame clears, the alerts come back
    Given the flame alarm is counting down "FLAME clearing 1s"
    And the coolant alarm is on
    When the countdown ends
    Then OLED row 6 cycles the alerts again
    And OLED row 7 is blank
    And the segment display returns to its number and " Hot"

  Scenario: The piezo is silent through the countdown
    Given the flame alarm is counting down "FLAME clearing 59s"
    When I watch the displays for 10 seconds
    Then the piezo is silent
