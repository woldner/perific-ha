from __future__ import annotations

import asyncio
from collections.abc import Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING, NotRequired, TypedDict

from homeassistant.helpers.storage import Store

from .api import PerificMeterSample
from .const import DOMAIN

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .api import PerificMeterData

STORAGE_VERSION = 1
STORAGE_KEY = f"{DOMAIN}.grid_power_samples"


class StoredMeterSample(TypedDict):
    item_id: str
    import_energy_kwh: float
    export_energy_kwh: float
    timestamp: int
    grid_power_w: NotRequired[float | None]


@dataclass(frozen=True, slots=True)
class PerificStoredGridPowerState:
    sample: PerificMeterSample
    data: PerificMeterData | None


class PerificGridPowerSampleStore:
    def __init__(self, hass: HomeAssistant) -> None:
        self._store = Store[dict[str, StoredMeterSample]](
            hass,
            STORAGE_VERSION,
            STORAGE_KEY,
            private=True,
        )
        self._data: dict[str, StoredMeterSample] | None = None
        self._data_lock = asyncio.Lock()

    async def async_load_sample(self, entry_id: str) -> PerificMeterSample | None:
        stored_state = await self.async_load_state(entry_id)
        if stored_state is None:
            return None
        return stored_state.sample

    async def async_load_state(
        self,
        entry_id: str,
    ) -> PerificStoredGridPowerState | None:
        async with self._data_lock:
            data = await self._async_load_data()
            stored_sample = data.get(entry_id)
        if stored_sample is None:
            return None
        return _state_from_storage(stored_sample)

    async def async_save_sample(
        self,
        entry_id: str,
        sample: PerificMeterSample,
    ) -> None:
        await self.async_save_state(
            entry_id,
            PerificStoredGridPowerState(sample=sample, data=None),
        )

    async def async_save_state(
        self,
        entry_id: str,
        state: PerificStoredGridPowerState,
    ) -> None:
        async with self._data_lock:
            data = await self._async_load_data()
            data[entry_id] = _state_to_storage(state)
            await self._store.async_save(data)

    async def async_remove_sample(self, entry_id: str) -> None:
        async with self._data_lock:
            data = await self._async_load_data()
            if data.pop(entry_id, None) is not None:
                await self._store.async_save(data)

    async def _async_load_data(self) -> dict[str, StoredMeterSample]:
        if self._data is None:
            self._data = dict(await self._store.async_load() or {})
        return self._data


def _sample_to_storage(sample: PerificMeterSample) -> StoredMeterSample:
    return {
        "item_id": sample.item_id,
        "import_energy_kwh": sample.import_energy_kwh,
        "export_energy_kwh": sample.export_energy_kwh,
        "timestamp": sample.timestamp,
    }


def _state_to_storage(state: PerificStoredGridPowerState) -> StoredMeterSample:
    return _sample_to_storage(state.sample)


def _sample_from_storage(
    stored_sample: Mapping[str, object],
) -> PerificMeterSample | None:
    item_id = stored_sample.get("item_id")
    import_energy_kwh = stored_sample.get("import_energy_kwh")
    export_energy_kwh = stored_sample.get("export_energy_kwh")
    timestamp = stored_sample.get("timestamp")
    if not isinstance(item_id, str):
        return None
    if not _is_number(import_energy_kwh) or not _is_number(export_energy_kwh):
        return None
    if not _is_int(timestamp):
        return None
    return PerificMeterSample(
        item_id=item_id,
        import_energy_kwh=float(import_energy_kwh),
        export_energy_kwh=float(export_energy_kwh),
        timestamp=timestamp,
    )


def _state_from_storage(
    stored_sample: object,
) -> PerificStoredGridPowerState | None:
    if not isinstance(stored_sample, Mapping):
        return None
    sample = _sample_from_storage(stored_sample)
    if sample is None:
        return None
    return PerificStoredGridPowerState(sample=sample, data=None)


def _is_number(value: object) -> bool:
    return not isinstance(value, bool) and isinstance(value, int | float)


def _is_int(value: object) -> bool:
    return not isinstance(value, bool) and isinstance(value, int)
