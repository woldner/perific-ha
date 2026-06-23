from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.const import EntityCategory
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import GRID_POWER_STATUS_READY
from .const import (
    BINARY_SENSOR_GRID_POWER_READY_KEY,
    CONF_ITEM_ID,
    CONF_USER_ID,
    DOMAIN,
)
from .coordinator import PerificDataUpdateCoordinator

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

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
    CoordinatorEntity[PerificDataUpdateCoordinator],
    BinarySensorEntity,
):
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: PerificDataUpdateCoordinator,
        entry: ConfigEntry,
        description: BinarySensorEntityDescription,
    ) -> None:
        super().__init__(coordinator)
        user_id = str(entry.data[CONF_USER_ID])
        item_id = str(entry.data[CONF_ITEM_ID])
        self.entity_description = description
        self._attr_unique_id = f"{DOMAIN}_{user_id}_{item_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{user_id}_{item_id}")},
            manufacturer="Perific/Enegic",
            name="Perific meter",
        )

    @property
    def available(self) -> bool:
        return super().available and self.coordinator.data is not None

    @property
    def is_on(self) -> bool | None:
        if self.coordinator.data is None:
            return None
        return (
            self.coordinator.data.grid_power_w is not None
            and self.coordinator.data.status == GRID_POWER_STATUS_READY
        )
