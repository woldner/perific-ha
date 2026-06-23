from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import EntityCategory, UnitOfPower

from .api import GRID_POWER_STATUS_OPTIONS
from .const import (
    SENSOR_GRID_POWER_KEY,
    SENSOR_GRID_POWER_STATUS_KEY,
    SENSOR_LAST_METER_SAMPLE_KEY,
)
from .entity import PerificEntity

if TYPE_CHECKING:
    from collections.abc import Mapping

    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .coordinator import PerificDataUpdateCoordinator

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
    SensorEntityDescription(
        key=SENSOR_LAST_METER_SAMPLE_KEY,
        translation_key=SENSOR_LAST_METER_SAMPLE_KEY,
        device_class=SensorDeviceClass.TIMESTAMP,
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
        _sensor_for_description(coordinator, entry, description)
        for description in SENSOR_DESCRIPTIONS
    )


class PerificSensor(
    PerificEntity,
    SensorEntity,
):
    def __init__(
        self,
        coordinator: PerificDataUpdateCoordinator,
        entry: ConfigEntry,
        description: SensorEntityDescription,
    ) -> None:
        super().__init__(coordinator, entry, description)

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


class PerificLastMeterSampleSensor(PerificSensor):
    @property
    def native_value(self) -> datetime | None:
        if self.coordinator.data is None or self.coordinator.data.timestamp is None:
            return None
        return datetime.fromtimestamp(
            self.coordinator.data.timestamp / 1000,
            tz=UTC,
        )


def _sensor_for_description(
    coordinator: PerificDataUpdateCoordinator,
    entry: ConfigEntry,
    description: SensorEntityDescription,
) -> PerificSensor:
    if description.key == SENSOR_GRID_POWER_STATUS_KEY:
        return PerificGridPowerStatusSensor(coordinator, entry, description)
    if description.key == SENSOR_LAST_METER_SAMPLE_KEY:
        return PerificLastMeterSampleSensor(coordinator, entry, description)
    return PerificGridPowerSensor(coordinator, entry, description)
