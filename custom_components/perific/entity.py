from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_ITEM_ID, CONF_USER_ID, DOMAIN
from .coordinator import PerificDataUpdateCoordinator

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.helpers.entity import EntityDescription


class PerificEntity(CoordinatorEntity[PerificDataUpdateCoordinator]):
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: PerificDataUpdateCoordinator,
        entry: ConfigEntry,
        description: EntityDescription,
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
