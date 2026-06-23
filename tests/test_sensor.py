from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace
from typing import TYPE_CHECKING, cast

import pytest

from custom_components.perific.api import (
    GRID_POWER_STATUS_BASELINE_REQUIRED,
    GRID_POWER_STATUS_OPTIONS,
    GRID_POWER_STATUS_READY,
    GRID_POWER_STATUS_STALE_PHASE_MINUTE,
    PerificMeterData,
)
from custom_components.perific.const import (
    CONF_ITEM_ID,
    CONF_USER_ID,
    SENSOR_GRID_POWER_STATUS_KEY,
)
from custom_components.perific.sensor import (
    SENSOR_DESCRIPTIONS,
    PerificGridPowerSensor,
    PerificGridPowerStatusSensor,
)

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry

    from custom_components.perific.coordinator import PerificDataUpdateCoordinator

GRID_POWER_W = 1234.5
STALE_SOURCE_TIMESTAMP = 1782120000000
SOURCE_TIMESTAMP = 1782120060000


def test_grid_power_sensor_reports_ready_watts() -> None:
    sensor = _sensor(
        data=PerificMeterData(
            item_id="meter-a",
            grid_power_w=GRID_POWER_W,
            timestamp=SOURCE_TIMESTAMP,
            status=GRID_POWER_STATUS_READY,
        ),
    )

    assert sensor.available
    assert sensor.native_value == pytest.approx(GRID_POWER_W)
    assert sensor.extra_state_attributes == {
        "grid_power_status": GRID_POWER_STATUS_READY,
        "source_timestamp": SOURCE_TIMESTAMP,
    }


def test_grid_power_sensor_keeps_baseline_wait_available_without_value() -> None:
    sensor = _sensor(
        data=PerificMeterData(
            item_id="meter-a",
            grid_power_w=None,
            timestamp=1782120000000,
            status=GRID_POWER_STATUS_BASELINE_REQUIRED,
        ),
    )

    assert sensor.available
    assert sensor.native_value is None
    assert sensor.extra_state_attributes == {
        "grid_power_status": GRID_POWER_STATUS_BASELINE_REQUIRED,
        "source_timestamp": 1782120000000,
    }


def test_grid_power_sensor_keeps_stale_minute_available_without_value() -> None:
    sensor = _sensor(
        data=PerificMeterData(
            item_id="meter-a",
            grid_power_w=None,
            timestamp=STALE_SOURCE_TIMESTAMP,
            status=GRID_POWER_STATUS_STALE_PHASE_MINUTE,
        ),
    )

    assert sensor.available
    assert sensor.native_value is None
    assert sensor.extra_state_attributes == {
        "grid_power_status": GRID_POWER_STATUS_STALE_PHASE_MINUTE,
        "source_timestamp": STALE_SOURCE_TIMESTAMP,
    }


def test_grid_power_sensor_unavailable_when_coordinator_update_failed() -> None:
    sensor = _sensor(
        data=PerificMeterData(
            item_id="meter-a",
            grid_power_w=GRID_POWER_W,
            timestamp=SOURCE_TIMESTAMP,
        ),
        last_update_success=False,
    )

    assert not sensor.available


def test_grid_power_sensor_unavailable_before_coordinator_data() -> None:
    sensor = _sensor(data=None)

    assert not sensor.available
    assert sensor.native_value is None
    assert sensor.extra_state_attributes is None


def test_grid_power_status_sensor_reports_status_as_enum() -> None:
    sensor = _status_sensor(
        data=PerificMeterData(
            item_id="meter-a",
            grid_power_w=None,
            timestamp=SOURCE_TIMESTAMP,
            status=GRID_POWER_STATUS_BASELINE_REQUIRED,
        ),
    )

    assert sensor.available
    assert sensor.native_value == GRID_POWER_STATUS_BASELINE_REQUIRED
    assert set(sensor.entity_description.options or []) == set(
        GRID_POWER_STATUS_OPTIONS
    )


def test_grid_power_status_sensor_unavailable_when_coordinator_update_failed() -> None:
    sensor = _status_sensor(
        data=PerificMeterData(
            item_id="meter-a",
            grid_power_w=GRID_POWER_W,
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
) -> PerificGridPowerSensor:
    entry = SimpleNamespace(
        data={
            CONF_USER_ID: "user-1",
            CONF_ITEM_ID: "meter-a",
        },
    )
    return PerificGridPowerSensor(
        cast(
            "PerificDataUpdateCoordinator",
            FakeCoordinator(data=data, last_update_success=last_update_success),
        ),
        cast("ConfigEntry", entry),
        SENSOR_DESCRIPTIONS[0],
    )


def _status_sensor(
    *,
    data: PerificMeterData | None,
    last_update_success: bool = True,
) -> PerificGridPowerStatusSensor:
    entry = SimpleNamespace(
        data={
            CONF_USER_ID: "user-1",
            CONF_ITEM_ID: "meter-a",
        },
    )
    description = next(
        description
        for description in SENSOR_DESCRIPTIONS
        if description.key == SENSOR_GRID_POWER_STATUS_KEY
    )
    return PerificGridPowerStatusSensor(
        cast(
            "PerificDataUpdateCoordinator",
            FakeCoordinator(data=data, last_update_success=last_update_success),
        ),
        cast("ConfigEntry", entry),
        description,
    )
