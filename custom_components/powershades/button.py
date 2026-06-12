"""PowerShades button platform."""
from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import PowerShadesConfigEntry, PowerShadesCoordinator

_LOGGER = logging.getLogger(__name__)

PARALLEL_UPDATES = 0


@dataclass(frozen=True, kw_only=True)
class PowerShadesButtonDescription(ButtonEntityDescription):
    """Describes a PowerShades button."""

    press_fn: Callable[[PowerShadesCoordinator], Awaitable[None]]


BUTTONS: tuple[PowerShadesButtonDescription, ...] = (
    PowerShadesButtonDescription(
        key="toggle",
        name="Toggle Shade",
        icon="mdi:swap-vertical",
        press_fn=lambda coordinator: coordinator.async_toggle(),
    ),
    PowerShadesButtonDescription(
        key="set_upper_limit",
        name="Set Upper Limit",
        icon="mdi:arrow-up-bold-circle",
        entity_category=EntityCategory.CONFIG,
        press_fn=lambda coordinator: coordinator.async_set_upper_limit(),
    ),
    PowerShadesButtonDescription(
        key="set_lower_limit",
        name="Set Lower Limit",
        icon="mdi:arrow-down-bold-circle",
        entity_category=EntityCategory.CONFIG,
        press_fn=lambda coordinator: coordinator.async_set_lower_limit(),
    ),
    PowerShadesButtonDescription(
        key="clear_limits",
        name="Clear Limits",
        icon="mdi:eraser",
        entity_category=EntityCategory.CONFIG,
        press_fn=lambda coordinator: coordinator.async_clear_limits(),
    ),
    PowerShadesButtonDescription(
        key="step_up",
        name="Step Up",
        icon="mdi:arrow-up",
        entity_category=EntityCategory.CONFIG,
        press_fn=lambda coordinator: coordinator.async_step_up(),
    ),
    PowerShadesButtonDescription(
        key="step_down",
        name="Step Down",
        icon="mdi:arrow-down",
        entity_category=EntityCategory.CONFIG,
        press_fn=lambda coordinator: coordinator.async_step_down(),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PowerShadesConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up PowerShades buttons from a config entry."""
    coordinator = entry.runtime_data
    async_add_entities(
        PowerShadesButton(coordinator, description)
        for description in BUTTONS
    )


class PowerShadesButton(
    CoordinatorEntity[PowerShadesCoordinator], ButtonEntity
):
    """PowerShades button entity."""

    _attr_has_entity_name = True
    entity_description: PowerShadesButtonDescription

    def __init__(
        self,
        coordinator: PowerShadesCoordinator,
        description: PowerShadesButtonDescription,
    ) -> None:
        """Initialize the PowerShades button."""
        super().__init__(coordinator)
        self.entity_description = description
        if coordinator.serial_number:
            self._attr_unique_id = (
                f"{DOMAIN}_{coordinator.serial_number}_{description.key}"
            )
        else:
            self._attr_unique_id = (
                f"{DOMAIN}_{coordinator.entry_id}_{description.key}"
            )
        self._attr_device_info = coordinator.device_info

    async def async_press(self) -> None:
        """Handle the button press."""
        await self.entity_description.press_fn(self.coordinator)
