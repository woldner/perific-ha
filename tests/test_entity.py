from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace
from typing import TYPE_CHECKING, cast

from custom_components.perific.binary_sensor import (
    BINARY_SENSOR_DESCRIPTIONS,
    PerificGridPowerReadyBinarySensor,
)
from custom_components.perific.const import CONF_ITEM_ID, CONF_USER_ID, DOMAIN
from custom_components.perific.sensor import SENSOR_DESCRIPTIONS, PerificGridPowerSensor

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry

    from custom_components.perific.api import PerificMeterData
    from custom_components.perific.coordinator import PerificDataUpdateCoordinator


def test_grid_power_sensor_and_ready_gate_share_meter_identity() -> None:
    entry = cast(
        "ConfigEntry",
        SimpleNamespace(
            data={
                CONF_USER_ID: "user-1",
                CONF_ITEM_ID: "meter-a",
            },
        ),
    )
    coordinator = cast(
        "PerificDataUpdateCoordinator",
        FakeCoordinator(data=None),
    )

    grid_power = PerificGridPowerSensor(coordinator, entry, SENSOR_DESCRIPTIONS[0])
    ready = PerificGridPowerReadyBinarySensor(
        coordinator,
        entry,
        BINARY_SENSOR_DESCRIPTIONS[0],
    )

    assert grid_power.device_info == ready.device_info
    assert grid_power.device_info["identifiers"] == {(DOMAIN, "user-1_meter-a")}
    assert grid_power.unique_id == "perific_user-1_meter-a_grid_power"
    assert ready.unique_id == "perific_user-1_meter-a_grid_power_ready"


@dataclass(slots=True)
class FakeCoordinator:
    data: PerificMeterData | None
    last_update_success: bool = True
