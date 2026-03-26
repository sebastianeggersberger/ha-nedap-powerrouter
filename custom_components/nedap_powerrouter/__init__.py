"""The Nedap PowerRouter integration.

This integration starts a local HTTP server (default port 8099) that receives
the POST requests from the Nedap PowerRouter (which normally sends data to
logging1.powerrouter.com). DNS must be redirected so that
logging1.powerrouter.com resolves to the Home Assistant host IP. A reverse
proxy (e.g. Synology DSM) forwards port 80 traffic to port 8099.

Optionally, received data can be forwarded to the real
logging1.powerrouter.com server so the Nedap portal stays up to date.

Protocol documented at: https://github.com/BenediktSeidl/prpd
"""

from __future__ import annotations

import logging
from typing import Any

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

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN]["server"] = server
    hass.data[DOMAIN]["powerrouter_id"] = "unknown"

    # Register a one-time callback to capture the powerrouter_id
    # from the first received message.
    def _capture_id(data: dict[str, Any]) -> None:
        header = data.get("header", {})
        pr_id = header.get("powerrouter_id", "unknown")
        if pr_id != "unknown":
            hass.data[DOMAIN]["powerrouter_id"] = pr_id
            _LOGGER.info("PowerRouter identified: %s", pr_id)
            server.remove_callback(_capture_id)

    server.register_callback(_capture_id)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    server: PowerRouterHTTPServer | None = hass.data[DOMAIN].get("server")
    if server:
        await server.stop()

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        hass.data.pop(DOMAIN, None)

    return unload_ok
