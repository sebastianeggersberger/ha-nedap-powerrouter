"""Sensor platform for Nedap PowerRouter integration.

Sensors are created dynamically when a PowerRouter is first discovered
(i.e. its first HTTP POST arrives). Each sensor is bound to a specific
powerrouter_id so that multiple PowerRouters on the same network are
fully supported without data mixing.
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, PARAM_MAP

_LOGGER = logging.getLogger(__name__)

# Map string device class names to SensorDeviceClass enum
DEVICE_CLASS_MAP: dict[str, SensorDeviceClass] = {
    "power": SensorDeviceClass.POWER,
    "energy": SensorDeviceClass.ENERGY,
    "voltage": SensorDeviceClass.VOLTAGE,
    "current": SensorDeviceClass.CURRENT,
    "temperature": SensorDeviceClass.TEMPERATURE,
    "frequency": SensorDeviceClass.FREQUENCY,
    "battery": SensorDeviceClass.BATTERY,
}

STATE_CLASS_MAP: dict[str, SensorStateClass] = {
    "measurement": SensorStateClass.MEASUREMENT,
    "total_increasing": SensorStateClass.TOTAL_INCREASING,
    "total": SensorStateClass.TOTAL,
}

# Module human-readable names for device grouping
MODULE_NAMES: dict[int, str] = {
    16: "Platform",
    9: "Wechselrichter (DC-AC)",
    11: "Netz (Carlo Gavazzi EM24)",
    12: "Solar",
    136: "Batterie",
}


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Nedap PowerRouter sensors from a config entry.

    Sensors are NOT created immediately. Instead, we register a discovery
    callback on the HTTP server. When a PowerRouter sends its first POST,
    the server fires the callback with the powerrouter_id, and we create
    all sensors for that device at that point.
    """
    entry_data = hass.data[DOMAIN][config_entry.entry_id]
    server = entry_data["server"]

    # Track which powerrouter_ids already have sensors
    created_devices: set[str] = set()

    def _on_device_discovered(powerrouter_id: str) -> None:
        """Handle discovery of a new PowerRouter."""
        if powerrouter_id in created_devices:
            return
        created_devices.add(powerrouter_id)

        _LOGGER.info(
            "Creating sensors for PowerRouter %s", powerrouter_id
        )
        sensors: list[SensorEntity] = _create_sensors_for_device(
            server, powerrouter_id
        )
        async_add_entities(sensors, update_before_add=False)

    server.register_discovery_callback(_on_device_discovered)

    # Also create sensors for any devices already discovered before
    # the sensor platform was set up (race condition guard).
    for pr_id in server.known_devices:
        _on_device_discovered(pr_id)


def _create_sensors_for_device(
    server: Any, powerrouter_id: str
) -> list[SensorEntity]:
    """Create all sensors for a single PowerRouter device."""
    sensors: list[SensorEntity] = []

    for module_id, params in PARAM_MAP.items():
        for param_key, (
            unique_suffix,
            name,
            unit,
            device_class_str,
            state_class_str,
            divisor,
        ) in params.items():
            sensors.append(
                PowerRouterSensor(
                    server=server,
                    module_id=module_id,
                    param_key=param_key,
                    unique_suffix=unique_suffix,
                    name=name,
                    unit=unit,
                    device_class_str=device_class_str,
                    state_class_str=state_class_str,
                    divisor=divisor,
                    powerrouter_id=powerrouter_id,
                )
            )

    # Computed sensors for the Energy Dashboard
    sensors.append(GridImportSensor(server, powerrouter_id))
    sensors.append(GridExportSensor(server, powerrouter_id))
    sensors.append(BatteryChargeSensor(server, powerrouter_id))
    sensors.append(BatteryDischargeSensor(server, powerrouter_id))

    return sensors


class PowerRouterSensor(SensorEntity):
    """A sensor reading one parameter from a specific PowerRouter."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(
        self,
        server: Any,
        module_id: int,
        param_key: str,
        unique_suffix: str,
        name: str,
        unit: str | None,
        device_class_str: str | None,
        state_class_str: str | None,
        divisor: float,
        powerrouter_id: str,
    ) -> None:
        """Initialise the sensor."""
        self._server = server
        self._module_id = module_id
        self._param_key = param_key
        self._divisor = divisor
        self._powerrouter_id = powerrouter_id

        self._attr_unique_id = f"nedap_pr_{powerrouter_id}_{unique_suffix}"
        self._attr_name = name
        self._attr_native_unit_of_measurement = unit
        self._attr_native_value: float | None = None

        if device_class_str and device_class_str in DEVICE_CLASS_MAP:
            self._attr_device_class = DEVICE_CLASS_MAP[device_class_str]
        if state_class_str and state_class_str in STATE_CLASS_MAP:
            self._attr_state_class = STATE_CLASS_MAP[state_class_str]

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        module_name = MODULE_NAMES.get(
            self._module_id, f"Module {self._module_id}"
        )
        return DeviceInfo(
            identifiers={
                (DOMAIN, f"{self._powerrouter_id}_{self._module_id}")
            },
            name=f"PowerRouter {module_name} ({self._powerrouter_id})",
            manufacturer="Nedap",
            model="PowerRouter",
            via_device=(DOMAIN, self._powerrouter_id),
        )

    async def async_added_to_hass(self) -> None:
        """Register per-device callback when added to hass."""
        self._server.register_device_callback(
            self._powerrouter_id, self._handle_data
        )

    async def async_will_remove_from_hass(self) -> None:
        """Remove per-device callback when removed from hass."""
        self._server.remove_device_callback(
            self._powerrouter_id, self._handle_data
        )

    @callback
    def _handle_data(self, data: dict[str, Any]) -> None:
        """Handle data from THIS PowerRouter only."""
        for module in data.get("module_statuses", []):
            if module.get("module_id") == self._module_id:
                raw_value = module.get(self._param_key)
                if raw_value is not None:
                    self._attr_native_value = round(
                        raw_value / self._divisor, 3
                    )
                    self.async_write_ha_state()
                break


class GridImportSensor(SensorEntity):
    """Computed sensor: Grid import energy (Netzbezug).

    For the HA Energy Dashboard "Grid consumption".
    Uses platform_energy_consumed (module 16, param_5).
    """

    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_name = "Netzbezug"
    _attr_native_unit_of_measurement = "kWh"
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_icon = "mdi:transmission-tower-import"

    def __init__(self, server: Any, powerrouter_id: str) -> None:
        """Initialise."""
        self._server = server
        self._powerrouter_id = powerrouter_id
        self._attr_unique_id = f"nedap_pr_{powerrouter_id}_grid_import"
        self._attr_native_value: float | None = None

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._powerrouter_id)},
            name=f"PowerRouter ({self._powerrouter_id})",
            manufacturer="Nedap",
            model="PowerRouter",
        )

    async def async_added_to_hass(self) -> None:
        """Register per-device callback."""
        self._server.register_device_callback(
            self._powerrouter_id, self._handle_data
        )

    async def async_will_remove_from_hass(self) -> None:
        """Remove per-device callback."""
        self._server.remove_device_callback(
            self._powerrouter_id, self._handle_data
        )

    @callback
    def _handle_data(self, data: dict[str, Any]) -> None:
        """Handle data — extract grid import energy."""
        for module in data.get("module_statuses", []):
            if module.get("module_id") == 16:
                raw = module.get("param_5")
                if raw is not None:
                    self._attr_native_value = round(raw / 1000, 3)
                    self.async_write_ha_state()
                break


class GridExportSensor(SensorEntity):
    """Computed sensor: Grid export energy (Netzeinspeisung).

    For the HA Energy Dashboard "Grid return".
    Uses platform_energy_produced (module 16, param_4).
    """

    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_name = "Netzeinspeisung"
    _attr_native_unit_of_measurement = "kWh"
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_icon = "mdi:transmission-tower-export"

    def __init__(self, server: Any, powerrouter_id: str) -> None:
        """Initialise."""
        self._server = server
        self._powerrouter_id = powerrouter_id
        self._attr_unique_id = f"nedap_pr_{powerrouter_id}_grid_export"
        self._attr_native_value: float | None = None

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._powerrouter_id)},
            name=f"PowerRouter ({self._powerrouter_id})",
            manufacturer="Nedap",
            model="PowerRouter",
        )

    async def async_added_to_hass(self) -> None:
        """Register per-device callback."""
        self._server.register_device_callback(
            self._powerrouter_id, self._handle_data
        )

    async def async_will_remove_from_hass(self) -> None:
        """Remove per-device callback."""
        self._server.remove_device_callback(
            self._powerrouter_id, self._handle_data
        )

    @callback
    def _handle_data(self, data: dict[str, Any]) -> None:
        """Handle data — extract grid export energy."""
        for module in data.get("module_statuses", []):
            if module.get("module_id") == 16:
                raw = module.get("param_4")
                if raw is not None:
                    self._attr_native_value = round(raw / 1000, 3)
                    self.async_write_ha_state()
                break

class BatteryChargeSensor(SensorEntity):
    """Computed sensor: Battery charge (Netzeinspeisung).

    For the HA Energy Dashboard "Battery return".
    Uses platform_energy_produced (module 136, param_3)."""

    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_name = "Batterie Geladen"
    _attr_native_unit_of_measurement = "kWh"
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_icon = "mdi:batterie-arrow-up"

    def __init__(self, server: Any, powerrouter_id: str) -> None:
        """Initialise."""
        self._server = server
        self._powerrouter_id = powerrouter_id
        self._attr_unique_id = f"nedap_pr_{powerrouter_id}_battery_charge"
        self._attr_native_value: float | None = None

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._powerrouter_id)},
            name=f"PowerRouter ({self._powerrouter_id})",
            manufacturer="Nedap",
            model="PowerRouter",
        )

    async def async_added_to_hass(self) -> None:
        """Register per-device callback."""
        self._server.register_device_callback(
            self._powerrouter_id, self._handle_data
        )

    async def async_will_remove_from_hass(self) -> None:
        """Remove per-device callback."""
        self._server.remove_device_callback(
            self._powerrouter_id, self._handle_data
        )

    @callback
    def _handle_data(self, data: dict[str, Any]) -> None:
        """Handle data — extract battery charged energy."""
        for module in data.get("module_statuses", []):
            if module.get("module_id") == 136:
                raw = module.get("param_3")
                if raw is not None:
                    self._attr_native_value = round(raw / 1000, 3)
                    self.async_write_ha_state()
                break

class BatteryDischargeSensor(SensorEntity):
    """Computed sensor: Battery discharge (Netzeinspeisung).

    For the HA Energy Dashboard "Battery consumption".
    Uses platform_energy_produced (module 16, param_4).
    """

    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_name = "Batterie Entladen"
    _attr_native_unit_of_measurement = "kWh"
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_icon = "mdi:batterie-arrow-down"
