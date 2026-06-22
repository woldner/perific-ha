from __future__ import annotations

import time
from dataclasses import dataclass
from typing import TYPE_CHECKING

from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import (
    FIELD_PHASE_MINUTE_STALE,
    GRID_POWER_STATUS_BASELINE_REQUIRED,
    GRID_POWER_STATUS_STALE_PHASE_MINUTE,
    MAX_PHASE_MINUTE_PACKET_AGE_SECONDS,
    MILLISECONDS_PER_SECOND,
    PerificAuthError,
    PerificDataError,
    PerificError,
    PerificMeterData,
    PerificMeterSample,
)
from .const import DOMAIN, LOGGER, SCAN_INTERVAL
from .store import PerificStoredGridPowerState

if TYPE_CHECKING:
    from collections.abc import Callable

    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant

    from .api import PerificClient
    from .meter import PerificGridPowerAccumulator
    from .store import PerificGridPowerSampleStore

AUTH_FAILURE_MESSAGE = "perific_auth_failed"
UPDATE_FAILURE_MESSAGE = "perific_update_failed"


def utcnow_milliseconds() -> int:
    return int(time.time() * MILLISECONDS_PER_SECOND)


@dataclass(frozen=True, slots=True)
class PerificCoordinatorRuntime:
    client: PerificClient
    item_id: str
    grid_power_accumulator: PerificGridPowerAccumulator
    sample_store: PerificGridPowerSampleStore
    now_ms: Callable[[], int] = utcnow_milliseconds


class PerificDataUpdateCoordinator(DataUpdateCoordinator[PerificMeterData]):
    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        runtime: PerificCoordinatorRuntime,
    ) -> None:
        super().__init__(
            hass,
            LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=SCAN_INTERVAL,
            always_update=False,
        )
        self._runtime = runtime

    async def _async_update_data(self) -> PerificMeterData:
        try:
            sample = await self._runtime.client.async_get_latest_meter_sample(
                item_id=self._runtime.item_id,
            )
            data = await self._async_update_from_sample(sample)
            if data is None:
                data = PerificMeterData(
                    item_id=sample.item_id,
                    grid_power_w=None,
                    timestamp=sample.timestamp,
                    status=GRID_POWER_STATUS_BASELINE_REQUIRED,
                )
        except PerificAuthError as err:
            raise ConfigEntryAuthFailed(AUTH_FAILURE_MESSAGE) from err
        except PerificDataError as err:
            if err.field == FIELD_PHASE_MINUTE_STALE:
                return await self._async_clear_stale_grid_power()
            raise UpdateFailed(UPDATE_FAILURE_MESSAGE) from err
        except PerificError as err:
            raise UpdateFailed(UPDATE_FAILURE_MESSAGE) from err
        else:
            return data

    async def _async_clear_stale_grid_power(self) -> PerificMeterData:
        accumulator = self._runtime.grid_power_accumulator
        previous_data = accumulator.last_data
        accumulator.last_data = None
        if accumulator.last_sample is not None and previous_data is not None:
            await self._runtime.sample_store.async_save_state(
                self.config_entry.entry_id,
                PerificStoredGridPowerState(
                    sample=accumulator.last_sample,
                    data=None,
                ),
            )
        return PerificMeterData(
            item_id=self._runtime.item_id,
            grid_power_w=None,
            timestamp=None,
            status=GRID_POWER_STATUS_STALE_PHASE_MINUTE,
        )

    def diagnostics(self) -> dict[str, object]:
        data = self.data
        if data is None:
            return {
                "grid_power_status": None,
                "has_grid_power": False,
                "last_update_success": self.last_update_success,
                "phase_minute_max_age_seconds": MAX_PHASE_MINUTE_PACKET_AGE_SECONDS,
            }

        return {
            "grid_power_status": data.status,
            "has_grid_power": data.grid_power_w is not None,
            "last_update_success": self.last_update_success,
            "phase_minute_max_age_seconds": MAX_PHASE_MINUTE_PACKET_AGE_SECONDS,
            "source_timestamp_age_seconds": _timestamp_age_seconds(
                data.timestamp,
                now_ms=self._runtime.now_ms(),
            ),
        }

    async def _async_update_from_sample(
        self,
        sample: PerificMeterSample,
    ) -> PerificMeterData | None:
        previous_timestamp = (
            self._runtime.grid_power_accumulator.last_sample.timestamp
            if self._runtime.grid_power_accumulator.last_sample is not None
            else None
        )
        previous_data = self._runtime.grid_power_accumulator.last_data
        try:
            return self._runtime.grid_power_accumulator.update(
                sample,
                now_ms=self._runtime.now_ms(),
            )
        finally:
            last_sample = self._runtime.grid_power_accumulator.last_sample
            last_data = self._runtime.grid_power_accumulator.last_data
            if last_sample == sample and (
                sample.timestamp != previous_timestamp or last_data != previous_data
            ):
                await self._runtime.sample_store.async_save_state(
                    self.config_entry.entry_id,
                    PerificStoredGridPowerState(sample=sample, data=last_data),
                )


def _timestamp_age_seconds(timestamp: int | None, *, now_ms: int) -> int | None:
    if timestamp is None:
        return None
    return max(0, (now_ms - timestamp) // MILLISECONDS_PER_SECOND)
