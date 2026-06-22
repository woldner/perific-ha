from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .api import (
    PerificAuthError,
    PerificClient,
    PerificConnectionError,
    PerificDataError,
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
    user_id: str


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1
    _reauth_username: str | None = None

    async def async_step_user(
        self,
        user_input: dict[str, str] | None = None,
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            validated = await self._async_validate_credentials(user_input, errors)
            if validated is not None:
                await self.async_set_unique_id(validated.user_id)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title="Perific", data=validated.data)

        return self.async_show_form(
            step_id="user",
            data_schema=_credentials_schema(),
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
                await self.async_set_unique_id(validated.user_id)
                self._abort_if_unique_id_mismatch(reason="wrong_account")
                return self.async_update_reload_and_abort(
                    self._get_reauth_entry(),
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
            if verify_meter:
                meter_data = await client.async_get_latest_meter_data()
                data[CONF_ITEM_ID] = meter_data.item_id
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
                user_id=auth.user_id,
            )

        return None


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
