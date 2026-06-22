from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.components.diagnostics import async_redact_data

from .const import CONF_ITEM_ID, CONF_TOKEN, CONF_USER_ID, CONF_USERNAME

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant

TO_REDACT = frozenset(
    {
        CONF_ITEM_ID,
        CONF_TOKEN,
        CONF_USERNAME,
        CONF_USER_ID,
        "account_id",
        "address",
        "email",
        "mac",
        "mac_address",
        "reporter_id",
        "serial",
        "token",
        "user_id",
    },
)


async def async_get_config_entry_diagnostics(
    _hass: HomeAssistant,
    entry: ConfigEntry,
) -> dict[str, Any]:
    return {"entry": async_redact_data(dict(entry.data), TO_REDACT)}
