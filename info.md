## Nedap PowerRouter Integration

Receive real-time data from your Nedap PowerRouter directly in Home Assistant – fully local, no cloud required.

**The mypowerrouter.com cloud platform will be shut down at the end of 2026.** This integration provides a local alternative.

### Features

- Receives PowerRouter data via local HTTP (DNS redirect)
- **Multi-device support**: Multiple PowerRouters automatically discovered by serial number
- Full Energy Dashboard compatibility (grid import/export, solar, battery)
- Optional forwarding to the real Nedap server
- 50+ sensors per PowerRouter across all modules

### How it works

The PowerRouter sends data every minute to `logging1.powerrouter.com`. By redirecting DNS to your Home Assistant host, this integration intercepts the data locally.

See the [README](https://github.com/sebastianeggersberger/ha-nedap-powerrouter) for full setup instructions.

### Tested with

- Nedap PowerRouter PR50SBi-BS (Firmware 8.0.10)
- Home Assistant 2026.3 (Home Assistant Container)
