"""Constants for the Nedap PowerRouter integration."""

DOMAIN = "nedap_powerrouter"
DEFAULT_PORT = 8099

# ──────────────────────────────────────────────────────────────
# Forwarding to the real logging1.powerrouter.com server.
# Because DNS is overridden locally, we must use the real IP.
# Resolve with: dig @8.8.8.8 logging1.powerrouter.com +short
# ──────────────────────────────────────────────────────────────
CONF_FORWARD_ENABLED = "forward_enabled"
CONF_FORWARD_IP = "forward_ip"
DEFAULT_FORWARD_ENABLED = False
DEFAULT_FORWARD_IP = ""
FORWARD_HOST_HEADER = "logging1.powerrouter.com"
FORWARD_PATH = "/logs.json"
FORWARD_TIMEOUT_SECONDS = 10

# ──────────────────────────────────────────────────────────────
# Module IDs as sent by the PowerRouter in the JSON POST body.
# Source: Photovoltaikforum / prpd / powerinterface projects.
# ──────────────────────────────────────────────────────────────

MODULE_PLATFORM = 16       # Platform / overall system
MODULE_DCAC = 9            # DC-AC converter (inverter to grid)
MODULE_GRID = 11           # Grid meter (Carlo Gavazzi EM24)
MODULE_SOLAR = 12          # Solar input(s)
MODULE_BATTERY = 136       # Battery module (if present)

# ──────────────────────────────────────────────────────────────
# Parameter mapping per module_id.
# Values are (param_key, human_name, unit, device_class,
#              state_class, divisor)
#
# Divisor: raw integer values need dividing:
#   - Voltages: /10 or /100 → V (EM24 grid: /10, others: /100)
#   - Currents: /100 → A
#   - Power: /1 → W (already in W, can be negative)
#   - Energy: /1000 → kWh (raw is in Wh)
#   - Frequency: /100 → Hz
#   - Temperature: /10 → °C
# ──────────────────────────────────────────────────────────────

PARAM_MAP = {
    MODULE_PLATFORM: {
        "param_0": ("platform_frequency", "Platform Frequenz", "Hz", "frequency", "measurement", 100),
        "param_1": ("platform_grid_voltage", "Platform Netzspannung", "V", "voltage", "measurement", 100),
        "param_2": ("platform_temperature", "Platform Temperatur", "°C", "temperature", "measurement", 10),
        "param_3": ("grid_power_total", "Netzleistung Gesamt", "W", "power", "measurement", 1),
        "param_4": ("platform_energy_produced", "Platform Energie Erzeugt", "kWh", "energy", "total_increasing", 1000),
        "param_5": ("platform_energy_consumed", "Platform Energie Verbraucht", "kWh", "energy", "total_increasing", 1000),
    },
    MODULE_DCAC: {
        "param_0": ("dcac_frequency", "Wechselrichter Frequenz", "Hz", "frequency", "measurement", 100),
        "param_1": ("dcac_grid_voltage", "Wechselrichter Netzspannung", "V", "voltage", "measurement", 100),
        "param_2": ("dcac_grid_power", "Wechselrichter Netzleistung", "W", "power", "measurement", 1),
        "param_3": ("dcac_energy_produced", "Wechselrichter Energie Erzeugt", "kWh", "energy", "total_increasing", 1000),
        "param_4": ("dcac_energy_consumed", "Wechselrichter Energie Verbraucht", "kWh", "energy", "total_increasing", 1000),
        "param_5": ("dcac_local_voltage", "Lokale Spannung", "V", "voltage", "measurement", 100),
        "param_6": ("dcac_local_power", "Lokale Leistung", "W", "power", "measurement", 1),
        "param_7": ("dcac_local_energy_consumed", "Lokal Verbrauchte Energie", "kWh", "energy", "total_increasing", 1000),
        "param_8": ("dcac_bus_voltage", "DC-Bus Spannung", "V", "voltage", "measurement", 100),
        "param_10": ("dcac_temperature", "Wechselrichter Temperatur", "°C", "temperature", "measurement", 10),
    },
    MODULE_GRID: {
        "param_0": ("grid_voltage_l1", "Netz Spannung L1", "V", "voltage", "measurement", 10),
        "param_1": ("grid_current_l1", "Netz Strom L1", "A", "current", "measurement", 100),
        "param_2": ("grid_power_l1", "Netz Leistung L1", "W", "power", "measurement", 1),
        "param_3": ("grid_energy_l1", "Netz Energie L1", "kWh", "energy", "total_increasing", 1000),
        "param_4": ("grid_voltage_l2", "Netz Spannung L2", "V", "voltage", "measurement", 10),
        "param_5": ("grid_current_l2", "Netz Strom L2", "A", "current", "measurement", 100),
        "param_6": ("grid_power_l2", "Netz Leistung L2", "W", "power", "measurement", 1),
        "param_7": ("grid_energy_l2", "Netz Energie L2", "kWh", "energy", "total_increasing", 1000),
        "param_8": ("grid_voltage_l3", "Netz Spannung L3", "V", "voltage", "measurement", 10),
        "param_9": ("grid_current_l3", "Netz Strom L3", "A", "current", "measurement", 100),
        "param_10": ("grid_power_l3", "Netz Leistung L3", "W", "power", "measurement", 1),
        "param_11": ("grid_energy_l3", "Netz Energie L3", "kWh", "energy", "total_increasing", 1000),
    },
    MODULE_SOLAR: {
        "param_0": ("solar_voltage_1", "Solar Spannung Eingang 1", "V", "voltage", "measurement", 100),
        "param_1": ("solar_current_1", "Solar Strom Eingang 1", "A", "current", "measurement", 100),
        "param_2": ("solar_power_1", "Solar Leistung Eingang 1", "W", "power", "measurement", 1),
        "param_3": ("solar_energy_1", "Solar Energie Eingang 1", "kWh", "energy", "total_increasing", 1000),
        "param_4": ("solar_temperature_1", "Solar Temperatur Eingang 1", "°C", "temperature", "measurement", 10),
        "param_5": ("solar_voltage_2", "Solar Spannung Eingang 2", "V", "voltage", "measurement", 100),
        "param_6": ("solar_current_2", "Solar Strom Eingang 2", "A", "current", "measurement", 100),
        "param_7": ("solar_power_2", "Solar Leistung Eingang 2", "W", "power", "measurement", 1),
        "param_8": ("solar_energy_2", "Solar Energie Eingang 2", "kWh", "energy", "total_increasing", 1000),
        "param_9": ("solar_temperature_2", "Solar Temperatur Eingang 2", "°C", "temperature", "measurement", 10),
        "param_10": ("solar_power_total", "Solar Leistung Gesamt", "W", "power", "measurement", 1),
        "param_11": ("solar_energy_total", "Solar Energie Gesamt", "kWh", "energy", "total_increasing", 1000),
    },
    MODULE_BATTERY: {
        "param_0": ("battery_voltage", "Batterie Spannung", "V", "voltage", "measurement", 100),
        "param_1": ("battery_current", "Batterie Strom", "A", "current", "measurement", 100),
        "param_2": ("battery_power", "Batterie Leistung", "W", "power", "measurement", 1),
        "param_3": ("battery_energy_charged", "Batterie Geladen", "kWh", "energy", "total_increasing", 1000),
        "param_4": ("battery_energy_discharged", "Batterie Entladen", "kWh", "energy", "total_increasing", 1000),
        "param_5": ("battery_soc", "Batterie Ladestand", "%", "battery", "measurement", 1),
        "param_6": ("battery_soc_max", "Batterie Wattstunden", "Wh", "kWh", "measurement", 1000),  # Vermutlich verfügbare Energie bis zum Entlademinimum in Wh
        "param_7": ("battery_temperature", "Batterie Temperatur", "°C", "temperature", "measurement", 10),
        "param_8": ("battery_module_temperature", "Batterie Modultemperatur", "°C", "temperature", "measurement", 10),  # Was incorrectly mapped as "battery_cycles" in v1.1.0
        "param_9": ("battery_charge_voltage", "Batterie Ladespannung", "V", "voltage", "measurement", 100),
        "param_10": ("battery_charge_current", "Batterie Ladestrom", "A", "current", "measurement", 100),
        "param_11": ("battery_discharge_voltage", "Batterie Entladespannung", "V", "voltage", "measurement", 100),
        "param_12": ("battery_discharge_current", "Batterie Entladestrom", "A", "current", "measurement", 100),
    },
}

# ──────────────────────────────────────────────────────────────
# Computed / virtual sensors for the HA Energy Dashboard.
# These are calculated from the raw module data.
# ──────────────────────────────────────────────────────────────

# For the Energy Dashboard we need:
#   - Grid consumption (Netzbezug) → energy, total_increasing, kWh
#   - Grid return (Netzeinspeisung) → energy, total_increasing, kWh
#   - Solar production → energy, total_increasing, kWh
#
# The grid power values from module 11 (Carlo Gavazzi EM24) are
# signed: positive = import from grid, negative = export to grid.
# The platform module 16 provides aggregated energy counters.
