# Priorities

Physical boat work — anything hands-on that isn't SignalK or embedded software
— is tracked in Evernote, not here. That's the authoritative list for what
Mark is actually working on aboard. This file is not the place to look up or
add a physical task, and the two overlapping in the short term is fine.

This file is for humans. High-level items only. Claude-session micro-tasks,
blocked questions, and detailed working state live in
`intermediate_files/claude_slop/kanban.md`, not here.

## Mark's list of physical tasks (potentially duplicates with evernote)
- water line from dripless needs to go somewhere real - engineroom air loop?
- small diy cockpit drain needs a new/diff fixture and hose going to stern
- freshwater pump (again)
- composting head
 - cut new square hpde for subfloor
 - epoxy down purpleheart base
 - screw in hpde (sealant around far edge of hpde)
 - epoxy around sole and hdpe
 - screw down brackets for airhead
 - run silicone line to shower sump (temp)
 - cut hole for fan
 - wire fan

## Mark's list of nits (gross!)
- runbook should say how to...
  - simulate a ping failure, and common things to check and try when there is a real failure
  - run book should say how to test ntfy locally
  - run book should say how to test pushover
  - others?
- i2c imu data isn't showing up in signalk - should it be configured via plugin or openplotter?
- unclear if temp sensors are just getting dropped or if they need new batteries


## In Progress
- Chain plate removal, cleaning, and resealing — 1 of the chain plates removed so far.
  - Next: take the removed chain plate to Ballard Sheet Metal for a fabrication quote.
- Electrical refit diagrams — DC system overview drafted and committed
  (`diagrams/electrical/`); next: rebuild with community Victron shapes.
  Detail in `intermediate_files/claude_slop/kanban.md`.

## Backlog

### Engine & mechanical / drivetrain
- Review overall engine state
- Permanent fix for prop shaft muff coupler (temporary solution currently in place)
- Install flame shield between fuel filter and engine
- Install radiator cap and coolant hoses

### Hull, bilge & underwater
- Clean rusted areas in bilge
- Repaint bilge (after rust cleanup)
- Clean rust off drive shaft
- Clean rust off shaft coupler
- De-rust topside (weather) deck

### Deck & rig
- Fix deck caulking; replace missing teak bungs
- Fix leaky deck boards / port stern deck leak
- Reseal small portholes; finish resealing large porthole; reseal butterfly hatches (partially done — revisit)
- Regrease all winch bearings; build box/jig for winch servicing
- Remove boomkin for rehab, refurb, reinstall
- Refinish wooden blocks/pulleys

### Plumbing & sanitation
- Address remaining holding tank system work now that the old tank is out
- Tighten head pump / apply sealant; install Y valve between Lectra-San and head
- Deep-clean water tank (due again)

### Electrical (core, non-IoT)
- Bring the second house battery into service — charge the spare pack to match
  before paralleling. *(Parked here for transfer to Evernote.)*
- GFCI outlet in head
- Secure batteries with straps; cover exposed positive battery terminals
- Wrap up DC-DC converter install (Victron Orion-Tr, purchased 2025-05-08)
- Charger for starter battery
- Research and diagram correct inverter / transfer-switch installation
- Install inverter and transfer switch correctly
- Install negative bus
- 3D-print negative bus base
- Design new positive bus
- Cut and drill new positive bus
- 3D-print positive bus base
- Design bus bar links
- Fabricate bus bar links
- Rework 3D-printed bus bar covers
- Design battery shelves
- Build battery shelves
- Design small battery holder
- 3D-print small battery holder
- Design pump circuits
- Short-term pump wiring
- Short-term shower sump wiring — white stripe is auto, solid brown is manual
- Design AC system
- Design pump system
- Design under-desk layout
- Design LED COB lighting
- Design CFL-to-LED replacements

### Interior & woodwork
- Refurb stern teak grid, bow pulpit floorboards, sink covers, hob cover
- Order replacement V-berth mattress

### Cleaning, painting & finish
- Paint engine panel
- Paint sole brace
- Paint chain locker cover
- Paint battery compartment
- Paint bilge
- De-rust rudder quadrant
- Paint/varnish rudder quadrant
- Cetol cockpit
- Cetol mid deck
- Cetol foredeck
- Topside paint: bowsprit
- Topside paint: general
- Refinish/refurb boom gallows
- Clean/wash cockpit
- Pressure wash cockpit

### Organization & storage
- Reorganize tool/parts drawers, galley, V-berth
- Pencil/utensil organizer, tool organizers for nav table

### Sharing & documentation
- Upload 3D models (e.g., deck fill cap keys) for others' benefit

### Still to buy
- Sanitation hose/fittings (1/2" and 1.5" clamps, Y connector, waste hose, PVC elbows)
- CO detector, propane sensor/alarm
- Manual bilge pump, floating winch handles, floating lanyard for deck key
- Ship's bell
- Sikasil N Plus (portlight gasket bedding), spare belt
- Fixed-mount VHF radio (Icom M10 Evo)
- Remote mic for fixed-mount VHF

### To sell / divest
- Spinnaker, Baba mainsail, other sails
- old autohelm components ?
- old radar monitor
- old plotter

## Someday/Maybe
- Watermaker
- Separate fridge/freezer
- Composting toilet
- Additional cabin heating
- Decide whether systems/*.md files should be tracked individually or left untracked until populated.

## SignalK / IoT — high level

Detailed state, evidence and micro-tasks for every item below live in
`intermediate_files/claude_slop/kanban.md`.

- Finish dockerizing the boat computer (Track B of
  `reference/containerization_strategy.md`; Dex, ntfy and QuestDB done)
- Migrate the history store from InfluxDB to QuestDB (decided 2026-08-18).
  InfluxDB backed up and verified, QuestDB running on the boat, and both the
  history plugin and Telegraf now recording into it alongside InfluxDB.
  Next is the multi-day soak and its parity checks, then retiring InfluxDB.
- Phone and audible delivery for vessel alarms (ntfy live both places;
  Pushover relay and speaker still open)
- Ansible for host provisioning (clock and watchdog roles first)
- Fit a DS3231 RTC; get GPS time off the N2K bus into chrony
- Rate-limit sshd (fail2ban or equivalent) — precautionary
- Rebuild boat computer (HALPI2 / HALOS decision; trial at home first)
- Decide boot media / SD-card strategy for the current Pi
- Sensors: engine temp and flow, rudder position, pump flow, air quality
  (BME680 ownership), pressure, illuminance, additional temperature
- Autopilot: pypilot, pypilot board, separate IMU
- Enclosures: 3D-print gas sensor / BME688 / IMU cases
- Cameras: interior and exterior Tapo cams
- Custom plugin ideas: COLREGs nav-light switching; single-path arithmetic
- Plugin housekeeping: nine major-version upgrades, broken/unconfigured
  plugins, barometric-drop notification
- MOB detection — research only; **never live-test the DSC emergency button**
  (standing rule)
- Install BLE hub for lighting and related devices
- Off-machine Vaultwarden hosting for the sops/age key backup
