"""Config flow for Nedap PowerRouter integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult

from .const import (
    CONF_FORWARD_ENABLED,
    CONF_FORWARD_IP,
    DEFAULT_FORWARD_ENABLED,
    DEFAULT_FORWARD_IP,
    DEFAULT_PORT,
    DOMAIN,
)


class NedapPowerRouterConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Nedap PowerRouter."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        # Only allow one instance
        if self._async_current_entries():
            return self.async_abort(reason="already_configured")

        if user_input is not None:
            return self.async_create_entry(
                title="Nedap PowerRouter",
                data=user_input,
            )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required("port", default=DEFAULT_PORT): vol.All(
                        int, vol.Range(min=1, max=65535)
                    ),
                    vol.Optional(
                        CONF_FORWARD_ENABLED,
                        default=DEFAULT_FORWARD_ENABLED,
                    ): bool,
                    vol.Optional(
                        CONF_FORWARD_IP,
                        default=DEFAULT_FORWARD_IP,
                    ): str,
                }
            ),
        )
