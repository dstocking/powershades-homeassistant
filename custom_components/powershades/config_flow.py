"""Config flow for the PowerShades integration."""
from __future__ import annotations

import ipaddress
import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult

from .const import DOMAIN
from .udp import (
    PowerShadesTimeoutError,
    async_discover_devices,
    async_get_device_info,
)

_LOGGER = logging.getLogger(__name__)

MANUAL_ENTRY = "manual"


class PowerShadesConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a PowerShades config flow."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._discovered: dict[str, dict] = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step: discover devices on the network."""
        discovered = await async_discover_devices(self.hass)
        self._discovered = {device["ip"]: device for device in discovered}
        if not self._discovered:
            return await self.async_step_manual()
        return await self.async_step_pick_device()

    async def async_step_pick_device(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Let the user pick a discovered device."""
        errors: dict[str, str] = {}

        if user_input is not None:
            choice = user_input["device"]
            if choice == MANUAL_ENTRY:
                return await self.async_step_manual()
            result = await self._async_validate_and_create(choice, errors)
            if result is not None:
                return result

        choices = {
            ip: f"{ip} (Serial: {device['serial']})"
            for ip, device in self._discovered.items()
        }
        choices[MANUAL_ENTRY] = "Enter IP address manually"

        return self.async_show_form(
            step_id="pick_device",
            data_schema=vol.Schema({vol.Required("device"): vol.In(choices)}),
            errors=errors,
        )

    async def async_step_manual(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle manual IP entry."""
        errors: dict[str, str] = {}

        if user_input is not None:
            ip = user_input["ip"].strip()
            try:
                ipaddress.IPv4Address(ip)
            except ValueError:
                errors["ip"] = "invalid_ip"
            else:
                result = await self._async_validate_and_create(ip, errors)
                if result is not None:
                    return result

        return self.async_show_form(
            step_id="manual",
            data_schema=vol.Schema({vol.Required("ip"): str}),
            errors=errors,
        )

    async def _async_validate_and_create(
        self, ip: str, errors: dict[str, str]
    ) -> ConfigFlowResult | None:
        """Probe the device and create the entry, or record an error."""
        try:
            info = await async_get_device_info(ip)
        except PowerShadesTimeoutError:
            _LOGGER.debug("Device at %s did not respond to probe", ip)
            errors["base"] = "cannot_connect"
            return None

        await self.async_set_unique_id(str(info["serial"]))
        self._abort_if_unique_id_configured(updates={"ip": ip})

        name = info["name"]
        title = f"PowerShade {name}" if name else f"PowerShade {ip}"
        return self.async_create_entry(
            title=title,
            data={"ip": ip, "serial": info["serial"], "name": name},
        )
