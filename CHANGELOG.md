# Changelog

All notable changes to the Nedap PowerRouter Home Assistant integration.

## [1.2.0] - 2026-07-02

### Fixed

- **Spurious zero values in energy counters:** The PowerRouter occasionally sends a sporadic `0` for lifetime energy counters (e.g. `solar_energy_total`), which Home Assistant interpreted as a meter reset and corrupted the long-term statistics for the whole day. All `total_increasing` sensors (incl. Netzbezug/Netzeinspeisung) are now protected by a plausibility filter: values below the last accepted reading are discarded and logged as a warning. A genuine meter reset is accepted after 3 consecutive consistent readings below the old level.
- **Battery SOC scaling:** Divisor changed from /10 to /1 – `battery_soc` now shows 100 % instead of 10.0 (#3, thanks @WhatGravity). If your model now shows 10× too much, please report it – the scaling may be model-specific.

### Changed

- **`battery_soc_max` (param_6) reinterpreted:** The parameter is presumably the available energy down to the discharge floor, not a "Max SoC". The sensor is now called "Batterie Verfügbare Energie" (Wh, `device_class: energy_storage`, divisor /1). Entity ID/unique ID remain unchanged (from PR #5, thanks @WhatGravity).

### Added

- **New battery diagnostic sensors** (param_9–12, from PR #5, thanks @WhatGravity): Ladespannung (V), Ladestrom (A), Entladespannung (V), Entladestrom (A) – mostly static charge/discharge limits, shown under "Diagnose" on the device page.
- **README – FRITZ!Box Option B:** Redirect via the FRITZ!Box upstream DNS (Internet → Zugangsdaten → DNS-Server), incl. note on PowerRouter DNS caching (#2, thanks @WhatGravity).
- **README – Variante D:** DNS override and port forwarding without Pi-hole/AdGuard using a dedicated Raspberry Pi with dnsmasq + iptables, e.g. for QNAP setups without a port-80 reverse proxy (#6, thanks @Timsche2210).

## [1.1.1] - 2026-04-01

### Fixed

- **Platform & inverter frequency divisor:** Changed from /1000 to /100 – frequency sensors now correctly show ~50 Hz instead of ~5 Hz (affected `platform_frequency` and `dcac_frequency`).
- **Battery param_8 mapping:** Corrected from "Batterie Zyklen" (battery cycles) to "Batterie Modultemperatur" (battery module temperature, °C, divisor /10). Confirmed by community testing on PR50SB-SU/S240.

### Notes

- `battery_soc_max` (param_6) may not be available on all PowerRouter models (e.g. PR50SB-SU/S240). The sensor will simply show "Unknown" if the parameter is not present in the data.
- If you previously relied on `sensor.*_battery_cycles`, this entity will be replaced by `sensor.*_battery_module_temperature` after updating. You may need to update any automations or dashboard cards referencing the old entity.

## [1.1.0] - 2026-03

### Added

- **Multi-device support:** Multiple PowerRouters on the same network are automatically discovered by serial number and created as separate devices with individual sensors.
- Dynamic sensor creation via discovery callbacks.
- Per-device callback architecture in the HTTP server.

## [1.0.0] - 2026-02

### Initial release

- Local HTTP receiver for Nedap PowerRouter data (DNS redirect approach).
- Full sensor set: Platform, DC-AC inverter, Grid (3-phase), Solar (2 inputs), Battery.
- Energy Dashboard compatibility (grid import/export, solar, battery).
- Optional data forwarding to the real Nedap server.
- HACS compatible.
