from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, ClassVar

from custom_components.perific import store as store_module
from custom_components.perific.api import PerificMeterSample
from custom_components.perific.store import (
    PerificGridPowerSampleStore,
    StoredMeterSample,
)

if TYPE_CHECKING:
    import pytest
    from homeassistant.core import HomeAssistant


async def test_grid_power_sample_store_round_trips_sample(
    hass: HomeAssistant,
) -> None:
    sample = PerificMeterSample(
        item_id="meter-a",
        import_energy_kwh=1000.167,
        export_energy_kwh=10.0,
        timestamp=1782120060000,
    )

    await PerificGridPowerSampleStore(hass).async_save_sample("entry-1", sample)

    assert (
        await PerificGridPowerSampleStore(hass).async_load_sample("entry-1") == sample
    )


async def test_grid_power_sample_store_rejects_extra_storage_fields(
    hass: HomeAssistant,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(store_module, "Store", StaticStorage)
    StaticStorage.initial_data = {
        "entry-1": {
            "item_id": "meter-a",
            "import_energy_kwh": 1000.167,
            "export_energy_kwh": 10.0,
            "timestamp": 1782120060000,
            "grid_power_w": 10020.0,
        },
    }

    assert await PerificGridPowerSampleStore(hass).async_load_sample("entry-1") is None


async def test_grid_power_sample_store_removes_sample(
    hass: HomeAssistant,
) -> None:
    sample = PerificMeterSample(
        item_id="meter-a",
        import_energy_kwh=1000.167,
        export_energy_kwh=10.0,
        timestamp=1782120060000,
    )
    store = PerificGridPowerSampleStore(hass)
    await store.async_save_sample("entry-1", sample)

    await store.async_remove_sample("entry-1")

    assert await store.async_load_sample("entry-1") is None


async def test_grid_power_sample_store_preserves_other_entries(
    hass: HomeAssistant,
) -> None:
    first_sample = PerificMeterSample(
        item_id="meter-a",
        import_energy_kwh=1000.167,
        export_energy_kwh=10.0,
        timestamp=1782120060000,
    )
    second_sample = PerificMeterSample(
        item_id="meter-b",
        import_energy_kwh=2000.167,
        export_energy_kwh=20.0,
        timestamp=1782120060000,
    )
    store = PerificGridPowerSampleStore(hass)
    await store.async_save_sample("entry-1", first_sample)
    await store.async_save_sample("entry-2", second_sample)

    await store.async_remove_sample("entry-1")

    assert await store.async_load_sample("entry-1") is None
    assert await store.async_load_sample("entry-2") == second_sample


async def test_grid_power_sample_store_ignores_malformed_entry(
    hass: HomeAssistant,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(store_module, "Store", StaticStorage)
    StaticStorage.initial_data = {"entry-1": "not-a-sample"}

    assert await PerificGridPowerSampleStore(hass).async_load_sample("entry-1") is None


async def test_grid_power_sample_store_serializes_concurrent_initial_saves(
    hass: HomeAssistant,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(store_module, "Store", DelayedStorage)
    store = PerificGridPowerSampleStore(hass)
    storage = DelayedStorage.latest
    assert storage is not None
    first_sample = PerificMeterSample(
        item_id="meter-a",
        import_energy_kwh=1000.167,
        export_energy_kwh=10.0,
        timestamp=1782120060000,
    )
    second_sample = PerificMeterSample(
        item_id="meter-b",
        import_energy_kwh=2000.167,
        export_energy_kwh=20.0,
        timestamp=1782120060000,
    )

    first_save = asyncio.create_task(
        store.async_save_sample("entry-1", first_sample),
    )
    second_save = asyncio.create_task(
        store.async_save_sample("entry-2", second_sample),
    )
    await storage.load_started.wait()
    await asyncio.sleep(0)
    storage.release_load.set()

    await asyncio.gather(first_save, second_save)

    assert await store.async_load_sample("entry-1") == first_sample
    assert await store.async_load_sample("entry-2") == second_sample


class DelayedStorage:
    latest: ClassVar[DelayedStorage | None] = None

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        self.data: dict[str, StoredMeterSample] = {}
        self.load_started = asyncio.Event()
        self.release_load = asyncio.Event()
        DelayedStorage.latest = self

    def __class_getitem__(cls, _item: object) -> type[DelayedStorage]:
        return cls

    async def async_load(self) -> dict[str, StoredMeterSample]:
        self.load_started.set()
        await self.release_load.wait()
        return dict(self.data)

    async def async_save(self, data: dict[str, StoredMeterSample]) -> None:
        self.data = dict(data)


class StaticStorage:
    initial_data: ClassVar[dict[str, object]] = {}
    latest: ClassVar[StaticStorage | None] = None

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        self.data: dict[str, object] = dict(self.initial_data)
        StaticStorage.latest = self

    def __class_getitem__(cls, _item: object) -> type[StaticStorage]:
        return cls

    async def async_load(self) -> dict[str, object]:
        return dict(self.data)

    async def async_save(self, data: dict[str, StoredMeterSample]) -> None:
        self.data = dict(data)
