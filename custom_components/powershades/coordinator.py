"""PowerShades data update coordinator."""
from __future__ import annotations

import logging
from dataclasses import dataclass, replace
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .const import (
    DOMAIN,
    LIMIT_LOWER,
    LIMIT_UPPER,
    OP_CLEAR_LIMITS,
    OP_GET_STATUS,
    OP_JOG_STOP,
    OP_SET_LIMIT,
    OP_SET_POSITION,
    OP_STEP_DOWN,
    OP_STEP_UP,
)
from .protocol import (
    StatusReply,
    battery_percentage,
    build_set_limit_payload,
    build_set_position_payload,
    parse_status_reply,
)
from .udp import PowerShadesConnection, PowerShadesTimeoutError

_LOGGER = logging.getLogger(__name__)

# Within this distance of the target the shade counts as arrived
POSITION_TOLERANCE = 2

PowerShadesConfigEntry = ConfigEntry["PowerShadesCoordinator"]


@dataclass(frozen=True)
class PowerShadesData:
    """State of one PowerShades device."""

    position: int | None = None
    battery_mv: int | None = None
    battery_percentage: int | None = None
    target_position: int | None = None


class PowerShadesCoordinator(DataUpdateCoordinator[PowerShadesData]):
    """Coordinator polling one PowerShades device and handling its pushes."""

    config_entry: PowerShadesConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        entry: PowerShadesConfigEntry,
        connection: PowerShadesConnection,
    ) -> None:
        """Initialize the coordinator."""
        self.connection = connection
        self.ip_address: str = entry.data["ip"]
        self.entry_id = entry.entry_id
        self.serial_number = entry.data.get("serial")
        self.device_name = entry.data.get("name")
        self._target_position: int | None = None
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=f"PowerShades {self.ip_address}",
            update_interval=timedelta(seconds=10),
        )
        connection.set_status_callback(self._handle_status_push)

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        if self.device_name:
            name = f"PowerShade {self.device_name}"
        else:
            name = f"PowerShade {self.ip_address}"

        if self.serial_number:
            identifiers = {(DOMAIN, str(self.serial_number))}
        else:
            identifiers = {(DOMAIN, self.entry_id)}

        return DeviceInfo(
            identifiers=identifiers,
            name=name,
            manufacturer="PowerShades",
            model="Motorized Window Cover",
            serial_number=str(
                self.serial_number) if self.serial_number else None,
        )

    def _data_from_status(self, status: StatusReply) -> PowerShadesData:
        if (
            self._target_position is not None
            and status.position is not None
            and abs(status.position - self._target_position)
            <= POSITION_TOLERANCE
        ):
            self._target_position = None
        return PowerShadesData(
            position=status.position,
            battery_mv=status.battery_mv,
            battery_percentage=battery_percentage(status.battery_mv),
            target_position=self._target_position,
        )

    @callback
    def _handle_status_push(self, status: StatusReply) -> None:
        """Handle a status packet (runs on the event loop)."""
        self.async_set_updated_data(self._data_from_status(status))

    async def _async_update_data(self) -> PowerShadesData:
        """Poll the device for status."""
        try:
            raw = await self.connection.async_request(OP_GET_STATUS)
        except PowerShadesTimeoutError as err:
            raise UpdateFailed(
                f"Shade at {self.ip_address} did not reply: {err}"
            ) from err
        status = parse_status_reply(raw)
        if status is None:
            raise UpdateFailed(
                f"Malformed status reply from {self.ip_address}")
        data = self._data_from_status(status)
        # Poll faster while the position is unknown
        self.update_interval = timedelta(
            seconds=5 if data.position is None else 10)
        return data

    def _set_target(self, position: int | None) -> None:
        """Update the movement target and notify entities immediately."""
        self._target_position = position
        if self.data is not None:
            self.async_set_updated_data(
                replace(self.data, target_position=position))

    async def async_set_position(self, position: int) -> None:
        """Move the shade to a position (0=closed, 100=open)."""
        self._set_target(position)
        self.connection.send(
            OP_SET_POSITION, build_set_position_payload(position))
        await self.async_request_refresh()

    async def async_stop(self) -> None:
        """Stop shade movement."""
        self._set_target(None)
        self.connection.send(OP_JOG_STOP)
        await self.async_request_refresh()

    async def async_toggle(self) -> None:
        """Toggle the shade: stop if moving, otherwise open/close."""
        data = self.data
        if data is None or data.position is None:
            _LOGGER.warning(
                "Cannot toggle shade %s: position unknown", self.ip_address)
            return
        if data.target_position is not None:
            await self.async_stop()
        elif data.position > 50:
            await self.async_set_position(0)
        else:
            await self.async_set_position(100)

    async def async_set_upper_limit(self) -> None:
        """Set the upper limit (fully open position)."""
        self.connection.send(OP_SET_LIMIT, build_set_limit_payload(LIMIT_UPPER))
        _LOGGER.info("Setting upper limit for %s", self.ip_address)

    async def async_set_lower_limit(self) -> None:
        """Set the lower limit (fully closed position)."""
        self.connection.send(OP_SET_LIMIT, build_set_limit_payload(LIMIT_LOWER))
        _LOGGER.info("Setting lower limit for %s", self.ip_address)

    async def async_clear_limits(self) -> None:
        """Clear both limits."""
        self.connection.send(OP_CLEAR_LIMITS)
        _LOGGER.info("Clearing limits for %s", self.ip_address)

    async def async_step_up(self) -> None:
        """Move the motor up one step (for trimming limits)."""
        self.connection.send(OP_STEP_UP)

    async def async_step_down(self) -> None:
        """Move the motor down one step (for trimming limits)."""
        self.connection.send(OP_STEP_DOWN)
