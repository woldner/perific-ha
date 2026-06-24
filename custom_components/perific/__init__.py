from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from .const import CONF_ITEM_ID, CONF_TOKEN, DOMAIN

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant

    from .api import PerificClient
    from .coordinator import PerificDataUpdateCoordinator
    from .meter import PerificGridPowerAccumulator
    from .store import PerificGridPowerSampleStore

PLATFORMS = ("binary_sensor", "sensor")


@dataclass(slots=True)
class PerificRuntimeData:
    client: PerificClient
    coordinator: PerificDataUpdateCoordinator


@dataclass(slots=True)
class PerificDomainData:
    sample_store: PerificGridPowerSampleStore
    grid_power_accumulators: dict[str, PerificGridPowerAccumulator]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    from homeassistant.helpers.aiohttp_client import async_get_clientsession

    from .api import PerificClient
    from .coordinator import PerificCoordinatorRuntime, PerificDataUpdateCoordinator
    from .meter import PerificGridPowerAccumulator

    client = PerificClient(
        async_get_clientsession(hass),
        token=str(entry.data[CONF_TOKEN]),
    )
    domain_data = get_domain_data(hass)
    sample_store = domain_data.sample_store
    stored_sample = await sample_store.async_load_sample(entry.entry_id)
    grid_power_accumulator = domain_data.grid_power_accumulators.setdefault(
        entry.entry_id,
        PerificGridPowerAccumulator(
            last_data=None,
            last_sample=stored_sample,
        ),
    )
    coordinator = PerificDataUpdateCoordinator(
        hass,
        entry,
        PerificCoordinatorRuntime(
            client=client,
            item_id=str(entry.data[CONF_ITEM_ID]),
            grid_power_accumulator=grid_power_accumulator,
            sample_store=sample_store,
        ),
    )
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = PerificRuntimeData(client=client, coordinator=coordinator)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        get_domain_data(hass).grid_power_accumulators.pop(entry.entry_id, None)
    return unloaded


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    domain_data = get_domain_data(hass)

    domain_data.grid_power_accumulators.pop(entry.entry_id, None)
    await domain_data.sample_store.async_remove_sample(entry.entry_id)


def get_domain_data(hass: HomeAssistant) -> PerificDomainData:
    from .store import PerificGridPowerSampleStore

    domain_data = hass.data.get(DOMAIN)
    if isinstance(domain_data, PerificDomainData):
        return domain_data
    domain_data = PerificDomainData(
        sample_store=PerificGridPowerSampleStore(hass),
        grid_power_accumulators={},
    )
    hass.data[DOMAIN] = domain_data
    return domain_data
