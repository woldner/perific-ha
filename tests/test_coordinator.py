from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, cast

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.perific.api import (
    FIELD_PHASE_MINUTE_STALE,
    GRID_POWER_STATUS_BASELINE_REQUIRED,
    GRID_POWER_STATUS_READY,
    GRID_POWER_STATUS_STALE_PHASE_MINUTE,
    MAX_PHASE_MINUTE_PACKET_AGE_SECONDS,
    PerificClient,
    PerificDataError,
    PerificMeterData,
    PerificMeterSample,
)
from custom_components.perific.const import DOMAIN
from custom_components.perific.coordinator import (
    PerificCoordinatorRuntime,
    PerificDataUpdateCoordinator,
)
from custom_components.perific.meter import (
    MAX_GRID_POWER_STATE_AGE_SECONDS,
    PerificGridPowerAccumulator,
)
from custom_components.perific.store import PerificStoredGridPowerState

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from custom_components.perific.store import PerificGridPowerSampleStore

SECOND_SAMPLE_TIMESTAMP = 1782120060000


class FakePerificClient:
    def __init__(self, samples: list[PerificMeterSample | Exception]) -> None:
        self.samples = samples
        self.requested_max_age_seconds: list[int | None] = []
        self.requested_item_ids: list[str | None] = []

    async def async_get_latest_meter_sample(
        self,
        *,
        item_id: str | None = None,
        max_age_seconds: int | None = MAX_PHASE_MINUTE_PACKET_AGE_SECONDS,
    ) -> PerificMeterSample:
        self.requested_max_age_seconds.append(max_age_seconds)
        self.requested_item_ids.append(item_id)
        result = self.samples.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


class FakeSampleStore:
    def __init__(self) -> None:
        self.saved_samples: list[tuple[str, PerificMeterSample]] = []
        self.saved_states: list[tuple[str, PerificStoredGridPowerState]] = []

    async def async_save_sample(
        self,
        entry_id: str,
        sample: PerificMeterSample,
    ) -> None:
        self.saved_samples.append((entry_id, sample))

    async def async_save_state(
        self,
        entry_id: str,
        state: PerificStoredGridPowerState,
    ) -> None:
        self.saved_states.append((entry_id, state))


@dataclass(frozen=True, slots=True)
class CoordinatorTestRuntime:
    client: FakePerificClient
    accumulator: PerificGridPowerAccumulator
    sample_store: FakeSampleStore
    now_ms: int = SECOND_SAMPLE_TIMESTAMP


async def test_coordinator_sets_unknown_data_without_grid_power_delta(
    hass: HomeAssistant,
) -> None:
    entry = _mock_entry(hass)
    sample = _meter_sample(
        import_energy_kwh=1000.000,
        timestamp=1782120000000,
    )
    client = FakePerificClient(
        [
            sample,
        ],
    )
    accumulator = PerificGridPowerAccumulator()
    sample_store = FakeSampleStore()
    coordinator = _coordinator(
        hass,
        entry,
        CoordinatorTestRuntime(client, accumulator, sample_store),
    )

    await coordinator.async_refresh()

    assert coordinator.last_update_success
    assert client.requested_max_age_seconds == [MAX_PHASE_MINUTE_PACKET_AGE_SECONDS]
    assert coordinator.data.grid_power_w is None
    assert coordinator.data.status == GRID_POWER_STATUS_BASELINE_REQUIRED
    assert coordinator.data.timestamp == sample.timestamp
    assert accumulator.last_sample == sample
    assert sample_store.saved_states == [
        (entry.entry_id, PerificStoredGridPowerState(sample=sample, data=None)),
    ]


async def test_coordinator_uses_baseline_from_previous_run(
    hass: HomeAssistant,
) -> None:
    entry = _mock_entry(hass)
    stored_sample = _meter_sample(
        import_energy_kwh=1000.000,
        timestamp=1782120000000,
    )
    current_sample = _meter_sample(
        import_energy_kwh=1000.167,
        timestamp=1782120060000,
    )
    accumulator = PerificGridPowerAccumulator(last_sample=stored_sample)
    client = FakePerificClient(
        [
            current_sample,
        ],
    )
    sample_store = FakeSampleStore()
    coordinator = _coordinator(
        hass,
        entry,
        CoordinatorTestRuntime(client, accumulator, sample_store),
    )
    await coordinator.async_refresh()

    assert coordinator.config_entry is entry
    assert coordinator.last_update_success
    assert coordinator.data.grid_power_w == pytest.approx(10020.0)
    assert coordinator.data.status == GRID_POWER_STATUS_READY
    assert client.requested_item_ids == ["meter-a"]
    assert len(sample_store.saved_states) == 1
    saved_entry_id, saved_state = sample_store.saved_states[0]
    assert saved_entry_id == entry.entry_id
    assert saved_state.sample == current_sample
    assert saved_state.data is not None
    assert saved_state.data.grid_power_w == pytest.approx(10020.0)


async def test_coordinator_reuses_fresh_stored_data_for_repeated_sample(
    hass: HomeAssistant,
) -> None:
    entry = _mock_entry(hass)
    stored_sample = _meter_sample(
        import_energy_kwh=1000.167,
        timestamp=SECOND_SAMPLE_TIMESTAMP,
    )
    stored_data = PerificMeterData(
        item_id="meter-a",
        grid_power_w=10020.0,
        timestamp=SECOND_SAMPLE_TIMESTAMP,
    )
    accumulator = PerificGridPowerAccumulator(
        last_data=stored_data,
        last_sample=stored_sample,
    )
    client = FakePerificClient([stored_sample])
    sample_store = FakeSampleStore()
    coordinator = _coordinator(
        hass,
        entry,
        CoordinatorTestRuntime(
            client,
            accumulator,
            sample_store,
            now_ms=SECOND_SAMPLE_TIMESTAMP + 60_000,
        ),
    )

    await coordinator.async_refresh()

    assert coordinator.last_update_success
    assert coordinator.data == stored_data
    assert sample_store.saved_states == []


async def test_coordinator_clears_stale_stored_data_for_repeated_sample(
    hass: HomeAssistant,
) -> None:
    entry = _mock_entry(hass)
    stored_sample = _meter_sample(
        import_energy_kwh=1000.167,
        timestamp=SECOND_SAMPLE_TIMESTAMP,
    )
    accumulator = PerificGridPowerAccumulator(
        last_data=PerificMeterData(
            item_id="meter-a",
            grid_power_w=10020.0,
            timestamp=SECOND_SAMPLE_TIMESTAMP,
        ),
        last_sample=stored_sample,
    )
    client = FakePerificClient([stored_sample])
    sample_store = FakeSampleStore()
    coordinator = _coordinator(
        hass,
        entry,
        CoordinatorTestRuntime(
            client,
            accumulator,
            sample_store,
            now_ms=SECOND_SAMPLE_TIMESTAMP
            + ((MAX_GRID_POWER_STATE_AGE_SECONDS + 1) * 1000),
        ),
    )

    await coordinator.async_refresh()

    assert coordinator.last_update_success
    assert coordinator.data.grid_power_w is None
    assert sample_store.saved_states == [
        (
            entry.entry_id,
            PerificStoredGridPowerState(sample=stored_sample, data=None),
        ),
    ]


async def test_coordinator_resets_expired_baseline_without_setup_failure(
    hass: HomeAssistant,
) -> None:
    entry = _mock_entry(hass)
    stored_sample = _meter_sample(
        import_energy_kwh=1000.000,
        timestamp=1782120000000,
    )
    current_sample = _meter_sample(
        import_energy_kwh=1000.500,
        timestamp=1782120960001,
    )
    accumulator = PerificGridPowerAccumulator(last_sample=stored_sample)
    client = FakePerificClient(
        [
            current_sample,
        ],
    )
    sample_store = FakeSampleStore()
    coordinator = _coordinator(
        hass,
        entry,
        CoordinatorTestRuntime(client, accumulator, sample_store),
    )
    await coordinator.async_refresh()

    assert coordinator.last_update_success
    assert coordinator.data.grid_power_w is None
    assert coordinator.data.status == GRID_POWER_STATUS_BASELINE_REQUIRED
    assert coordinator.data.timestamp == current_sample.timestamp
    assert accumulator.last_sample == current_sample
    assert sample_store.saved_states == [
        (
            entry.entry_id,
            PerificStoredGridPowerState(sample=current_sample, data=None),
        ),
    ]


async def test_coordinator_loads_with_stale_packet_error_as_unknown_data(
    hass: HomeAssistant,
) -> None:
    entry = _mock_entry(hass)
    stale_error = PerificDataError(FIELD_PHASE_MINUTE_STALE)
    client = FakePerificClient([stale_error])
    accumulator = PerificGridPowerAccumulator()
    sample_store = FakeSampleStore()
    coordinator = _coordinator(
        hass,
        entry,
        CoordinatorTestRuntime(
            client,
            accumulator,
            sample_store,
            now_ms=1782129999000,
        ),
    )

    await coordinator.async_refresh()

    assert coordinator.last_update_success
    assert client.requested_max_age_seconds == [MAX_PHASE_MINUTE_PACKET_AGE_SECONDS]
    assert coordinator.data.item_id == "meter-a"
    assert coordinator.data.grid_power_w is None
    assert coordinator.data.status == GRID_POWER_STATUS_STALE_PHASE_MINUTE
    assert coordinator.data.timestamp is None
    assert accumulator.last_sample is None
    assert sample_store.saved_states == []


async def test_coordinator_clears_stored_data_on_stale_packet_error(
    hass: HomeAssistant,
) -> None:
    entry = _mock_entry(hass)
    stored_sample = _meter_sample(
        import_energy_kwh=1000.167,
        timestamp=SECOND_SAMPLE_TIMESTAMP,
    )
    stored_data = PerificMeterData(
        item_id="meter-a",
        grid_power_w=10020.0,
        timestamp=SECOND_SAMPLE_TIMESTAMP,
    )
    stale_error = PerificDataError(FIELD_PHASE_MINUTE_STALE)
    client = FakePerificClient([stale_error])
    accumulator = PerificGridPowerAccumulator(
        last_data=stored_data,
        last_sample=stored_sample,
    )
    sample_store = FakeSampleStore()
    coordinator = _coordinator(
        hass,
        entry,
        CoordinatorTestRuntime(client, accumulator, sample_store),
    )

    await coordinator.async_refresh()

    assert coordinator.last_update_success
    assert coordinator.data.grid_power_w is None
    assert coordinator.data.status == GRID_POWER_STATUS_STALE_PHASE_MINUTE
    assert coordinator.data.timestamp is None
    assert accumulator.last_sample == stored_sample
    assert accumulator.last_data is None
    assert sample_store.saved_states == [
        (
            entry.entry_id,
            PerificStoredGridPowerState(sample=stored_sample, data=None),
        ),
    ]


async def test_coordinator_does_not_persist_rejected_out_of_order_sample(
    hass: HomeAssistant,
) -> None:
    entry = _mock_entry(hass)
    stored_sample = _meter_sample(
        import_energy_kwh=1000.000,
        timestamp=1782120000000,
    )
    out_of_order_sample = _meter_sample(
        import_energy_kwh=999.900,
        timestamp=1782119940000,
    )
    accumulator = PerificGridPowerAccumulator(last_sample=stored_sample)
    client = FakePerificClient(
        [
            out_of_order_sample,
        ],
    )
    sample_store = FakeSampleStore()
    coordinator = _coordinator(
        hass,
        entry,
        CoordinatorTestRuntime(client, accumulator, sample_store),
    )
    await coordinator.async_refresh()

    assert not coordinator.last_update_success
    assert accumulator.last_sample == stored_sample
    assert sample_store.saved_states == []


async def test_coordinator_does_not_persist_single_counter_reset_candidate(
    hass: HomeAssistant,
) -> None:
    entry = _mock_entry(hass)
    stored_sample = _meter_sample(
        import_energy_kwh=1000.000,
        timestamp=1782120000000,
    )
    reset_candidate = _meter_sample(
        import_energy_kwh=0.001,
        timestamp=1782120060000,
    )
    accumulator = PerificGridPowerAccumulator(last_sample=stored_sample)
    client = FakePerificClient(
        [
            reset_candidate,
        ],
    )
    sample_store = FakeSampleStore()
    coordinator = _coordinator(
        hass,
        entry,
        CoordinatorTestRuntime(client, accumulator, sample_store),
    )
    await coordinator.async_refresh()

    assert coordinator.last_update_success
    assert coordinator.data.grid_power_w is None
    assert coordinator.data.status == GRID_POWER_STATUS_BASELINE_REQUIRED
    assert accumulator.last_sample == stored_sample
    assert accumulator.counter_reset_candidate == reset_candidate
    assert sample_store.saved_states == []


async def test_coordinator_diagnostics_explain_unknown_grid_power(
    hass: HomeAssistant,
) -> None:
    entry = _mock_entry(hass)
    sample = _meter_sample(
        import_energy_kwh=1000.000,
        timestamp=1782120000000,
    )
    coordinator = _coordinator(
        hass,
        entry,
        CoordinatorTestRuntime(
            FakePerificClient([sample]),
            PerificGridPowerAccumulator(),
            FakeSampleStore(),
            now_ms=1782120030000,
        ),
    )

    await coordinator.async_refresh()

    assert coordinator.diagnostics() == {
        "grid_power_status": GRID_POWER_STATUS_BASELINE_REQUIRED,
        "has_grid_power": False,
        "last_update_success": True,
        "phase_minute_max_age_seconds": MAX_PHASE_MINUTE_PACKET_AGE_SECONDS,
        "source_timestamp_age_seconds": 30,
    }


def _coordinator(
    hass: HomeAssistant,
    entry: MockConfigEntry,
    runtime: CoordinatorTestRuntime,
) -> PerificDataUpdateCoordinator:
    return PerificDataUpdateCoordinator(
        hass,
        entry,
        PerificCoordinatorRuntime(
            client=cast("PerificClient", runtime.client),
            item_id="meter-a",
            grid_power_accumulator=runtime.accumulator,
            sample_store=cast("PerificGridPowerSampleStore", runtime.sample_store),
            now_ms=lambda: runtime.now_ms,
        ),
    )


def _mock_entry(hass: HomeAssistant) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Perific",
        unique_id="user-1",
        data={},
    )
    entry.add_to_hass(hass)
    return entry


def _meter_sample(
    *,
    import_energy_kwh: float,
    timestamp: int,
    export_energy_kwh: float = 10.0,
    item_id: str = "meter-a",
) -> PerificMeterSample:
    return PerificMeterSample(
        item_id=item_id,
        import_energy_kwh=import_energy_kwh,
        export_energy_kwh=export_energy_kwh,
        timestamp=timestamp,
    )
