from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import UnitOfPower
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import GRID_POWER_STATUS_OPTIONS
from .const import (
    CONF_ITEM_ID,
    CONF_USER_ID,
    DOMAIN,
    SENSOR_GRID_POWER_KEY,
    SENSOR_GRID_POWER_STATUS_KEY,
)
from .coordinator import PerificDataUpdateCoordinator

if TYPE_CHECKING:
    from collections.abc import Mapping

    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

SENSOR_DESCRIPTIONS = (
    SensorEntityDescription(
        key=SENSOR_GRID_POWER_KEY,
        translation_key=SENSOR_GRID_POWER_KEY,
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key=SENSOR_GRID_POWER_STATUS_KEY,
        translation_key=SENSOR_GRID_POWER_STATUS_KEY,
        device_class=SensorDeviceClass.ENUM,
        options=list(GRID_POWER_STATUS_OPTIONS),
    ),
)


async def async_setup_entry(
    _hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data.coordinator
    async_add_entities(
        _sensor_for_description(coordinator, entry, description)
        for description in SENSOR_DESCRIPTIONS
    )


class PerificSensor(
    CoordinatorEntity[PerificDataUpdateCoordinator],
    SensorEntity,
):
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: PerificDataUpdateCoordinator,
        entry: ConfigEntry,
        description: SensorEntityDescription,
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
    def extra_state_attributes(self) -> Mapping[str, str | int | None] | None:
        if self.coordinator.data is None:
            return None
        return {
            "source_timestamp": self.coordinator.data.timestamp,
        }


class PerificGridPowerSensor(PerificSensor):
    @property
    def native_value(self) -> float | None:
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.grid_power_w

    @property
    def extra_state_attributes(self) -> Mapping[str, str | int | None] | None:
        if self.coordinator.data is None:
            return None
        return {
            **(super().extra_state_attributes or {}),
            "grid_power_status": self.coordinator.data.status,
        }


class PerificGridPowerStatusSensor(PerificSensor):
    @property
    def native_value(self) -> str | None:
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.status


def _sensor_for_description(
    coordinator: PerificDataUpdateCoordinator,
    entry: ConfigEntry,
    description: SensorEntityDescription,
) -> PerificSensor:
    if description.key == SENSOR_GRID_POWER_STATUS_KEY:
        return PerificGridPowerStatusSensor(coordinator, entry, description)
    return PerificGridPowerSensor(coordinator, entry, description)
