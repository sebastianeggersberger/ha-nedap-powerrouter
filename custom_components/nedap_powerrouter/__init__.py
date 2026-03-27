"""The Nedap PowerRouter integration.

This integration starts a local HTTP server (default port 8099) that receives
the POST requests from one or more Nedap PowerRouters (which normally send
data to logging1.powerrouter.com). DNS must be redirected so that
logging1.powerrouter.com resolves to the Home Assistant host IP. A reverse
proxy (e.g. Synology DSM) forwards port 80 traffic to port 8099.

Multiple PowerRouters are automatically discovered and separated by their
unique serial number (powerrouter_id). Sensors are created dynamically
when each device sends its first POST.

Optionally, received data can be forwarded to the real
logging1.powerrouter.com server so the Nedap portal stays up to date.

Protocol documented at: https://github.com/BenediktSeidl/prpd
"""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import (
    CONF_FORWARD_ENABLED,
    CONF_FORWARD_IP,
    DEFAULT_FORWARD_ENABLED,
    DEFAULT_FORWARD_IP,
    DEFAULT_PORT,
    DOMAIN,
)
from .server import PowerRouterHTTPServer

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Nedap PowerRouter from a config entry."""
    port: int = entry.data.get("port", DEFAULT_PORT)
    forward_enabled: bool = entry.data.get(
        CONF_FORWARD_ENABLED, DEFAULT_FORWARD_ENABLED
    )
    forward_ip: str = entry.data.get(CONF_FORWARD_IP, DEFAULT_FORWARD_IP)

    server = PowerRouterHTTPServer(
        port=port,
        forward_enabled=forward_enabled,
        forward_ip=forward_ip,
    )
    await server.start()

    # Store data per config entry (not globally) for clean unload
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "server": server,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    entry_data = hass.data[DOMAIN].get(entry.entry_id, {})
    server: PowerRouterHTTPServer | None = entry_data.get("server")
    if server:
        await server.stop()

    unload_ok = await hass.config_entries.async_unload_platforms(
        entry, PLATFORMS
    )

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
        if not hass.data[DOMAIN]:
            hass.data.pop(DOMAIN, None)

    return unload_ok
