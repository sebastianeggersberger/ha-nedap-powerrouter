# Changelog

All notable changes to the Nedap PowerRouter Home Assistant integration.

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
