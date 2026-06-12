"""The PowerShades integration."""
from __future__ import annotations

import logging

from getmac import get_mac_address

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.device_registry import format_mac
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN
from .coordinator import PowerShadesConfigEntry, PowerShadesCoordinator
from .discovery import async_start_discovery
from .services import async_setup_services
from .udp import PowerShadesConnection

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.BUTTON, Platform.COVER, Platform.SENSOR]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def _async_update_mac(
    hass: HomeAssistant, entry: PowerShadesConfigEntry,
    coordinator: PowerShadesCoordinator,
) -> None:
    """Look up the shade's MAC via ARP and persist it on the entry.

    Called right after a successful first refresh, so the ARP cache is
    warm from the UDP exchange. Best-effort: silently keeps the entry
    unchanged when the MAC can't be determined (e.g. routed networks).
    """
    mac = await hass.async_add_executor_job(
        lambda: get_mac_address(ip=entry.data["ip"]))
    if mac is None or mac == "00:00:00:00:00:00":
        return
    mac = format_mac(mac)
    if mac != entry.data.get("mac"):
        _LOGGER.debug("Resolved MAC %s for shade %s", mac, entry.data["ip"])
        hass.config_entries.async_update_entry(
            entry, data={**entry.data, "mac": mac})
    coordinator.mac_address = mac


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the PowerShades component."""
    async_setup_services(hass)
    async_start_discovery(hass)
    return True


async def async_setup_entry(
    hass: HomeAssistant, entry: PowerShadesConfigEntry
) -> bool:
    """Set up PowerShades from a config entry."""
    connection = PowerShadesConnection(entry.data["ip"])
    await connection.async_connect()

    coordinator = PowerShadesCoordinator(hass, entry, connection)
    try:
        await coordinator.async_config_entry_first_refresh()
    except ConfigEntryNotReady:
        connection.close()
        raise

    entry.runtime_data = coordinator
    entry.async_on_unload(connection.close)

    await _async_update_mac(hass, entry, coordinator)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: PowerShadesConfigEntry
) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
