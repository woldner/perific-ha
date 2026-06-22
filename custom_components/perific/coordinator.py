from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import (
    PerificAuthError,
    PerificClient,
    PerificError,
    PerificMeterData,
)
from .const import DOMAIN, LOGGER, SCAN_INTERVAL

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

AUTH_FAILURE_MESSAGE = "perific_auth_failed"
UPDATE_FAILURE_MESSAGE = "perific_update_failed"


class PerificDataUpdateCoordinator(DataUpdateCoordinator[PerificMeterData]):
    def __init__(
        self,
        hass: HomeAssistant,
        client: PerificClient,
        *,
        item_id: str,
    ) -> None:
        super().__init__(
            hass,
            LOGGER,
            name=DOMAIN,
            update_interval=SCAN_INTERVAL,
            always_update=False,
        )
        self.client = client
        self.item_id = item_id

    async def _async_update_data(self) -> PerificMeterData:
        try:
            return await self.client.async_get_latest_meter_data(item_id=self.item_id)
        except PerificAuthError as err:
            raise ConfigEntryAuthFailed(AUTH_FAILURE_MESSAGE) from err
        except PerificError as err:
            raise UpdateFailed(UPDATE_FAILURE_MESSAGE) from err
