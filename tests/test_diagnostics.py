from __future__ import annotations

from types import SimpleNamespace
from typing import TYPE_CHECKING

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.perific.const import (
    CONF_ITEM_ID,
    CONF_TOKEN,
    CONF_USER_ID,
    CONF_USERNAME,
    DOMAIN,
)
from custom_components.perific.diagnostics import async_get_config_entry_diagnostics

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


async def test_diagnostics_redact_entry_data_and_include_telemetry(
    hass: HomeAssistant,
) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Perific",
        data={
            CONF_USERNAME: "user@example.com",
            CONF_TOKEN: "secret-token",
            CONF_USER_ID: "user-1",
            CONF_ITEM_ID: "meter-a",
        },
    )
    entry.add_to_hass(hass)
    entry.runtime_data = SimpleNamespace(coordinator=FakeCoordinator())

    assert await async_get_config_entry_diagnostics(hass, entry) == {
        "entry": {
            CONF_USERNAME: "**REDACTED**",
            CONF_TOKEN: "**REDACTED**",
            CONF_USER_ID: "**REDACTED**",
            CONF_ITEM_ID: "**REDACTED**",
        },
        "telemetry": {
            "grid_power_status": "baseline_required",
            "has_grid_power": False,
        },
    }


class FakeCoordinator:
    @staticmethod
    def diagnostics() -> dict[str, object]:
        return {
            "grid_power_status": "baseline_required",
            "has_grid_power": False,
        }
