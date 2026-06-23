from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.const import EntityCategory

from .api import GRID_POWER_STATUS_READY
from .const import (
    BINARY_SENSOR_GRID_POWER_READY_KEY,
)
from .entity import PerificEntity

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .coordinator import PerificDataUpdateCoordinator

BINARY_SENSOR_DESCRIPTIONS = (
    BinarySensorEntityDescription(
        key=BINARY_SENSOR_GRID_POWER_READY_KEY,
        translation_key=BINARY_SENSOR_GRID_POWER_READY_KEY,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
)


async def async_setup_entry(
    _hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data.coordinator
    async_add_entities(
        PerificGridPowerReadyBinarySensor(coordinator, entry, description)
        for description in BINARY_SENSOR_DESCRIPTIONS
    )


class PerificGridPowerReadyBinarySensor(
    PerificEntity,
    BinarySensorEntity,
):
    def __init__(
        self,
        coordinator: PerificDataUpdateCoordinator,
        entry: ConfigEntry,
        description: BinarySensorEntityDescription,
    ) -> None:
        super().__init__(coordinator, entry, description)

    @property
    def is_on(self) -> bool | None:
        if self.coordinator.data is None:
            return None
        return (
            self.coordinator.data.grid_power_w is not None
            and self.coordinator.data.status == GRID_POWER_STATUS_READY
        )
