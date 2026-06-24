from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
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
    SENSOR_LAST_METER_SAMPLE_KEY,
)
from custom_components.perific.sensor import (
    SENSOR_DESCRIPTIONS,
    PerificGridPowerSensor,
    PerificGridPowerStatusSensor,
    PerificLastMeterSampleSensor,
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


def test_grid_power_sensor_does_not_duplicate_meter_fact_attributes() -> None:
    sensor = _sensor(
        data=PerificMeterData(
            item_id="meter-a",
            grid_power_w=GRID_POWER_W,
            timestamp=SOURCE_TIMESTAMP,
            status=GRID_POWER_STATUS_READY,
        ),
    )
    attributes = sensor.extra_state_attributes or {}

    assert "grid_power_status" not in attributes
    assert "source_timestamp" not in attributes


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


def test_last_meter_sample_sensor_reports_source_timestamp() -> None:
    sensor = _last_meter_sample_sensor(
        data=PerificMeterData(
            item_id="meter-a",
            grid_power_w=None,
            timestamp=SOURCE_TIMESTAMP,
            status=GRID_POWER_STATUS_STALE_PHASE_MINUTE,
        ),
    )

    assert sensor.available
    assert sensor.native_value == datetime.fromtimestamp(
        SOURCE_TIMESTAMP / 1000,
        tz=UTC,
    )


def test_last_meter_sample_sensor_unavailable_when_coordinator_update_failed() -> None:
    sensor = _last_meter_sample_sensor(
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


def _last_meter_sample_sensor(
    *,
    data: PerificMeterData | None,
    last_update_success: bool = True,
) -> PerificLastMeterSampleSensor:
    entry = SimpleNamespace(
        data={
            CONF_USER_ID: "user-1",
            CONF_ITEM_ID: "meter-a",
        },
    )
    description = next(
        description
        for description in SENSOR_DESCRIPTIONS
        if description.key == SENSOR_LAST_METER_SAMPLE_KEY
    )
    return PerificLastMeterSampleSensor(
        cast(
            "PerificDataUpdateCoordinator",
            FakeCoordinator(data=data, last_update_success=last_update_success),
        ),
        cast("ConfigEntry", entry),
        description,
    )
