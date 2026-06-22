from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

import pytest
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    start_reauth_flow,
)

from custom_components.perific import config_flow
from custom_components.perific.api import (
    PerificAuth,
    PerificAuthError,
    PerificDataError,
    PerificMeterSample,
)
from custom_components.perific.const import (
    CONF_ITEM_ID,
    CONF_PASSWORD,
    CONF_TOKEN,
    CONF_TOKEN_VALID_TO,
    CONF_USER_ID,
    CONF_USERNAME,
    DOMAIN,
)

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


class FakePerificClient:
    fail_latest_meter_sample: ClassVar[bool] = False
    latest_meter_sample_error: ClassVar[Exception | None] = None
    requested_item_ids: ClassVar[list[str | None]] = []

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        pass

    async def async_authenticate(self, username: str, password: str) -> PerificAuth:
        self._username = username
        if password.startswith("bad"):
            raise PerificAuthError
        return PerificAuth(
            token=f"token-for-{username}",
            token_valid_to="2027-06-22T00:00:00",
            user_id="user-1",
        )

    async def async_get_latest_meter_sample(
        self,
        *,
        item_id: str | None = None,
        max_age_seconds: int | None = None,
    ) -> PerificMeterSample:
        assert max_age_seconds is None
        self.requested_item_ids.append(item_id)
        if self.latest_meter_sample_error is not None:
            raise self.latest_meter_sample_error
        if self.fail_latest_meter_sample:
            msg = "latest_meter_sample_failed"
            raise RuntimeError(msg)
        return PerificMeterSample(
            item_id=item_id or "meter-a",
            import_energy_kwh=1234.0,
            export_energy_kwh=0.0,
            timestamp=1782120000000,
        )


@pytest.fixture
def fake_perific_client(monkeypatch: pytest.MonkeyPatch) -> None:
    FakePerificClient.fail_latest_meter_sample = False
    FakePerificClient.latest_meter_sample_error = None
    FakePerificClient.requested_item_ids = []
    monkeypatch.setattr(config_flow, "PerificClient", FakePerificClient)


async def test_user_flow_stores_token_without_password(
    hass: HomeAssistant,
    enable_custom_integrations: None,
    fake_perific_client: None,
) -> None:
    assert enable_custom_integrations is None
    assert fake_perific_client is None

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
        data={
            CONF_USERNAME: "user@example.com",
            CONF_PASSWORD: "correct-password",
        },
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Perific"
    assert result["data"] == {
        CONF_USERNAME: "user@example.com",
        CONF_TOKEN: "token-for-user@example.com",
        CONF_TOKEN_VALID_TO: "2027-06-22T00:00:00",
        CONF_USER_ID: "user-1",
        CONF_ITEM_ID: "meter-a",
    }
    assert CONF_PASSWORD not in result["data"]


async def test_user_flow_reports_invalid_auth(
    hass: HomeAssistant,
    enable_custom_integrations: None,
    fake_perific_client: None,
) -> None:
    assert enable_custom_integrations is None
    assert fake_perific_client is None

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
        data={
            CONF_USERNAME: "user@example.com",
            CONF_PASSWORD: "bad-password",
        },
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}


async def test_user_flow_reports_multiple_meters(
    hass: HomeAssistant,
    enable_custom_integrations: None,
    fake_perific_client: None,
) -> None:
    assert enable_custom_integrations is None
    assert fake_perific_client is None
    FakePerificClient.latest_meter_sample_error = PerificDataError(
        "ItemId.ambiguous",
    )

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
        data={
            CONF_USERNAME: "user@example.com",
            CONF_PASSWORD: "correct-password",
        },
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "multiple_meters"}


async def test_reauth_preserves_configured_item_id(
    hass: HomeAssistant,
    enable_custom_integrations: None,
    fake_perific_client: None,
) -> None:
    assert enable_custom_integrations is None
    assert fake_perific_client is None
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Perific",
        unique_id="user-1",
        data={
            CONF_USERNAME: "user@example.com",
            CONF_TOKEN: "old-token",
            CONF_TOKEN_VALID_TO: "2026-06-22T00:00:00",
            CONF_USER_ID: "user-1",
            CONF_ITEM_ID: "meter-b",
        },
    )
    entry.add_to_hass(hass)

    result = await start_reauth_flow(hass, entry)

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_USERNAME: "user@example.com",
            CONF_PASSWORD: "correct-password",
        },
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert entry.data[CONF_ITEM_ID] == "meter-b"
    assert entry.data[CONF_TOKEN] == "token-for-user@example.com"
    assert FakePerificClient.requested_item_ids == []


async def test_reauth_does_not_require_meter_telemetry(
    hass: HomeAssistant,
    enable_custom_integrations: None,
    fake_perific_client: None,
) -> None:
    assert enable_custom_integrations is None
    assert fake_perific_client is None
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Perific",
        unique_id="user-1",
        data={
            CONF_USERNAME: "user@example.com",
            CONF_TOKEN: "old-token",
            CONF_TOKEN_VALID_TO: "2026-06-22T00:00:00",
            CONF_USER_ID: "user-1",
            CONF_ITEM_ID: "meter-b",
        },
    )
    entry.add_to_hass(hass)
    FakePerificClient.fail_latest_meter_sample = True

    result = await start_reauth_flow(hass, entry)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_USERNAME: "user@example.com",
            CONF_PASSWORD: "correct-password",
        },
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert entry.data[CONF_ITEM_ID] == "meter-b"
    assert entry.data[CONF_TOKEN] == "token-for-user@example.com"
    assert FakePerificClient.requested_item_ids == []
