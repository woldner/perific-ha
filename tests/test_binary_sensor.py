from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace
from typing import TYPE_CHECKING, cast

from homeassistant.const import EntityCategory

from custom_components.perific.api import (
    GRID_POWER_STATUS_BASELINE_REQUIRED,
    GRID_POWER_STATUS_READY,
    GRID_POWER_STATUS_STALE_PHASE_MINUTE,
    PerificMeterData,
)
from custom_components.perific.binary_sensor import (
    BINARY_SENSOR_DESCRIPTIONS,
    PerificGridPowerReadyBinarySensor,
)
from custom_components.perific.const import CONF_ITEM_ID, CONF_USER_ID

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry

    from custom_components.perific.coordinator import PerificDataUpdateCoordinator

SOURCE_TIMESTAMP = 1782120060000


def test_grid_power_ready_binary_sensor_turns_on_for_ready_watts() -> None:
    sensor = _sensor(
        data=PerificMeterData(
            item_id="meter-a",
            grid_power_w=1234.5,
            timestamp=SOURCE_TIMESTAMP,
            status=GRID_POWER_STATUS_READY,
        ),
    )

    assert sensor.available
    assert sensor.is_on
    assert sensor.entity_description.entity_category == EntityCategory.DIAGNOSTIC


def test_grid_power_ready_binary_sensor_turns_off_for_waiting_states() -> None:
    baseline_sensor = _sensor(
        data=PerificMeterData(
            item_id="meter-a",
            grid_power_w=None,
            timestamp=SOURCE_TIMESTAMP,
            status=GRID_POWER_STATUS_BASELINE_REQUIRED,
        ),
    )
    stale_sensor = _sensor(
        data=PerificMeterData(
            item_id="meter-a",
            grid_power_w=None,
            timestamp=SOURCE_TIMESTAMP,
            status=GRID_POWER_STATUS_STALE_PHASE_MINUTE,
        ),
    )

    assert baseline_sensor.available
    assert stale_sensor.available
    assert not baseline_sensor.is_on
    assert not stale_sensor.is_on


def test_grid_power_ready_binary_sensor_unavailable_without_data() -> None:
    sensor = _sensor(data=None)

    assert not sensor.available
    assert sensor.is_on is None


def test_grid_power_ready_binary_sensor_unavailable_on_update_failure() -> None:
    sensor = _sensor(
        data=PerificMeterData(
            item_id="meter-a",
            grid_power_w=1234.5,
            timestamp=SOURCE_TIMESTAMP,
            status=GRID_POWER_STATUS_READY,
        ),
        last_update_success=False,
    )

    assert not sensor.available


@dataclass(slots=True)
class FakeCoordinator:
    data: PerificMeterData | None
    last_update_success: bool = True


def _sensor(
    *,
    data: PerificMeterData | None,
    last_update_success: bool = True,
) -> PerificGridPowerReadyBinarySensor:
    entry = SimpleNamespace(
        data={
            CONF_USER_ID: "user-1",
            CONF_ITEM_ID: "meter-a",
        },
    )
    return PerificGridPowerReadyBinarySensor(
        cast(
            "PerificDataUpdateCoordinator",
            FakeCoordinator(data=data, last_update_success=last_update_success),
        ),
        cast("ConfigEntry", entry),
        BINARY_SENSOR_DESCRIPTIONS[0],
    )
