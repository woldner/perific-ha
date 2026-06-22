from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from .const import CONF_ITEM_ID, CONF_TOKEN

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant

    from .api import PerificClient
    from .coordinator import PerificDataUpdateCoordinator

PLATFORMS = ("sensor",)


@dataclass(slots=True)
class PerificRuntimeData:
    client: PerificClient
    coordinator: PerificDataUpdateCoordinator


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    from homeassistant.helpers.aiohttp_client import async_get_clientsession

    from .api import PerificClient
    from .coordinator import PerificDataUpdateCoordinator

    client = PerificClient(
        async_get_clientsession(hass),
        token=str(entry.data[CONF_TOKEN]),
    )
    coordinator = PerificDataUpdateCoordinator(
        hass,
        client,
        item_id=str(entry.data[CONF_ITEM_ID]),
    )
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = PerificRuntimeData(client=client, coordinator=coordinator)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
