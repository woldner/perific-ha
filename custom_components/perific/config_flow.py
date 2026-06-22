from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .api import (
    PerificAuthError,
    PerificClient,
    PerificConnectionError,
    PerificDataError,
    PerificMeterSample,
    PerificResponseError,
)
from .const import (
    CONF_ITEM_ID,
    CONF_PASSWORD,
    CONF_TOKEN,
    CONF_TOKEN_VALID_TO,
    CONF_USER_ID,
    CONF_USERNAME,
    DOMAIN,
)

if TYPE_CHECKING:
    from collections.abc import Mapping

    from homeassistant.config_entries import ConfigFlowResult


@dataclass(frozen=True, slots=True)
class ValidatedConfig:
    data: dict[str, str]
    meter_samples: tuple[PerificMeterSample, ...]
    user_id: str


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1
    _pending_config: ValidatedConfig | None = None
    _reauth_username: str | None = None

    async def async_step_user(
        self,
        user_input: dict[str, str] | None = None,
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            validated = await self._async_validate_credentials(user_input, errors)
            if validated is not None:
                self._pending_config = validated
                return await self.async_step_meter()

        return self.async_show_form(
            step_id="user",
            data_schema=_credentials_schema(),
            errors=errors,
        )

    async def async_step_meter(
        self,
        user_input: dict[str, str] | None = None,
    ) -> ConfigFlowResult:
        if self._pending_config is None:
            return await self.async_step_user()

        errors: dict[str, str] = {}
        meter_ids = {sample.item_id for sample in self._pending_config.meter_samples}
        if user_input is not None:
            item_id = user_input[CONF_ITEM_ID]
            if item_id in meter_ids:
                if self._async_entry_configured(
                    self._pending_config.user_id,
                    item_id,
                ):
                    return self.async_abort(reason="already_configured")
                data = dict(self._pending_config.data)
                data[CONF_ITEM_ID] = item_id
                await self.async_set_unique_id(
                    _entry_unique_id(self._pending_config.user_id, item_id),
                )
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title="Perific", data=data)
            errors["base"] = "invalid_meter"

        return self.async_show_form(
            step_id="meter",
            data_schema=_meter_schema(self._pending_config.meter_samples),
            errors=errors,
        )

    async def async_step_reauth(
        self,
        entry_data: Mapping[str, str],
    ) -> ConfigFlowResult:
        self._reauth_username = entry_data.get(CONF_USERNAME)
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self,
        user_input: dict[str, str] | None = None,
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            validated = await self._async_validate_credentials(
                user_input,
                errors,
                verify_meter=False,
            )
            if validated is not None:
                reauth_entry = self._get_reauth_entry()
                item_id = str(reauth_entry.data[CONF_ITEM_ID])
                await self.async_set_unique_id(
                    _reauth_unique_id(validated.user_id, item_id, reauth_entry),
                )
                self._abort_if_unique_id_mismatch(reason="wrong_account")
                return self.async_update_reload_and_abort(
                    reauth_entry,
                    data_updates=validated.data,
                )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=_credentials_schema(self._reauth_username),
            errors=errors,
        )

    async def _async_validate_credentials(
        self,
        user_input: Mapping[str, str],
        errors: dict[str, str],
        *,
        verify_meter: bool = True,
    ) -> ValidatedConfig | None:
        client = PerificClient(async_get_clientsession(self.hass))
        try:
            auth = await client.async_authenticate(
                user_input[CONF_USERNAME],
                user_input[CONF_PASSWORD],
            )
            data = {
                CONF_USERNAME: user_input[CONF_USERNAME],
                CONF_TOKEN: auth.token,
                CONF_TOKEN_VALID_TO: auth.token_valid_to,
                CONF_USER_ID: auth.user_id,
            }
            meter_samples = ()
            if verify_meter:
                meter_samples = await client.async_get_latest_meter_samples(
                    max_age_seconds=None,
                )
        except PerificAuthError:
            errors["base"] = "invalid_auth"
        except PerificConnectionError:
            errors["base"] = "cannot_connect"
        except PerificDataError:
            errors["base"] = "no_meter"
        except PerificResponseError:
            errors["base"] = "cannot_connect"
        else:
            return ValidatedConfig(
                data=data,
                meter_samples=meter_samples,
                user_id=auth.user_id,
            )

        return None

    def _async_entry_configured(self, user_id: str, item_id: str) -> bool:
        return any(
            entry.data.get(CONF_USER_ID) == user_id
            and entry.data.get(CONF_ITEM_ID) == item_id
            for entry in self._async_current_entries()
        )


def _credentials_schema(username: str | None = None) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(CONF_USERNAME, default=username): TextSelector(
                TextSelectorConfig(
                    type=TextSelectorType.EMAIL,
                    autocomplete="username",
                ),
            ),
            vol.Required(CONF_PASSWORD): TextSelector(
                TextSelectorConfig(
                    type=TextSelectorType.PASSWORD,
                    autocomplete="current-password",
                ),
            ),
        },
    )


def _meter_schema(meter_samples: tuple[PerificMeterSample, ...]) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(CONF_ITEM_ID): SelectSelector(
                SelectSelectorConfig(
                    options=[
                        SelectOptionDict(
                            value=sample.item_id,
                            label=f"Perific meter {sample.item_id}",
                        )
                        for sample in meter_samples
                    ],
                ),
            ),
        },
    )


def _entry_unique_id(user_id: str, item_id: str) -> str:
    return f"{user_id}_{item_id}"


def _reauth_unique_id(
    user_id: str,
    item_id: str,
    entry: config_entries.ConfigEntry,
) -> str:
    meter_unique_id = _entry_unique_id(user_id, item_id)
    if entry.unique_id == meter_unique_id:
        return meter_unique_id
    return user_id
