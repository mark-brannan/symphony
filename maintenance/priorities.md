# Priorities

## In Progress
- Chain plate removal, cleaning, and resealing — 1 of the chain plates removed so far.
  - Next: take the removed chain plate to Ballard Sheet Metal for a fabrication quote.

## Blocked

## Backlog

### Safety & compliance
- Monthly valve check (recurring — overdue, was due 2026-07-02)
- WA state vessel registration/decals renewal
- Halon system service/check
- Service fire extinguishers

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
- Drogue, HF radio, radar

## Someday/Maybe
- Watermaker
- Separate fridge/freezer
- Composting toilet
- Additional cabin heating
- Decide whether systems/*.md files should be tracked individually or left untracked until populated.

## SignalK / IoT

### Sensors
- Design engine temp sensors and diagram
- Design engine flow sensor plumbing
- Design engine flow sensor electrical
- Rudder position sensor
- Pump flow sensors
- Air quality sensors
- Air pressure sensor
- Illuminance sensor
- Additional temperature sensors
- Design smart pump system with voltage/current detection

### Autopilot
- pypilot
- Design pypilot board
- Separate IMU for pypilot

### Enclosures
- 3D-print gas sensor case
- 3D-print BME688 case
- 3D-print IMU case

### Infrastructure
- Finish dockerizing the boat computer — SignalK, Grafana, Dex, and Caddy run as
  native systemd services today; the repo's compose files and `RUNBOOK.md`
  describe the Docker deploy meant to replace them. Docker isn't installed on the
  Pi yet, so `docker compose --profile tls up` can't run there.
- Rebuild boat computer
- Install BLE hub for lighting and related devices
- Set up real off-machine hosting (VPS or existing NAS) for Vaultwarden to hold the sops/age key backup, reachable privately (e.g. Tailscale) — currently only a local Docker proof-of-concept on the boat computer, which doesn't yet solve the single-point-of-failure risk for the key protecting `symphony.sops.yaml` / `signalk/security.json`
- Configure InfluxDB to receive data from SignalK, with appropriate data retention policies
- Revisit current InfluxDB org/bucket setup (org "darkstarllc", bucket "symphony") — consider alternatives using multiple buckets aboard Symphony
- Set up Grafana dashboards based on the public examples on GitHub from @meri-imperiumi
- Evaluate Telegraf as a host-metrics adjunct to InfluxDB (CPU, memory, disk, temperature) — it was installed Nov 2024, never configured past the default stub, and removed Aug 2026 rather than left failing

### Cameras
- Identify location for interior Tapo cam
- Install Tapo cam for galley/saloon
- Identify location for exterior Tapo cam
- Install exterior Tapo cam
