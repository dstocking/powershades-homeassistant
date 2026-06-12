"""PowerShades sensor platform."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, UnitOfElectricPotential
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import (
    PowerShadesConfigEntry,
    PowerShadesCoordinator,
    PowerShadesData,
)

_LOGGER = logging.getLogger(__name__)

PARALLEL_UPDATES = 0


@dataclass(frozen=True, kw_only=True)
class PowerShadesSensorDescription(SensorEntityDescription):
    """Describes a PowerShades sensor."""

    value_fn: Callable[[PowerShadesData], int | None]


SENSORS: tuple[PowerShadesSensorDescription, ...] = (
    PowerShadesSensorDescription(
        key="battery",
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda data: data.battery_percentage,
    ),
    PowerShadesSensorDescription(
        key="voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricPotential.MILLIVOLT,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda data: data.battery_mv,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PowerShadesConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up PowerShades sensors from a config entry."""
    coordinator = entry.runtime_data
    async_add_entities(
        PowerShadesSensor(coordinator, description) for description in SENSORS
    )


class PowerShadesSensor(CoordinatorEntity[PowerShadesCoordinator], SensorEntity):
    """PowerShades diagnostic sensor."""

    _attr_has_entity_name = True
    entity_description: PowerShadesSensorDescription

    def __init__(
        self,
        coordinator: PowerShadesCoordinator,
        description: PowerShadesSensorDescription,
    ) -> None:
        """Initialize the PowerShades sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        if coordinator.serial_number:
            self._attr_unique_id = (
                f"{DOMAIN}_{coordinator.serial_number}_{description.key}"
            )
        else:
            self._attr_unique_id = f"{DOMAIN}_{coordinator.entry_id}_{description.key}"
        self._attr_device_info = coordinator.device_info

    @property
    def native_value(self) -> int | None:
        """Return the sensor value."""
        return self.entity_description.value_fn(self.coordinator.data)
