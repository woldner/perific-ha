from __future__ import annotations

from typing import TYPE_CHECKING

from custom_components.perific import PerificDomainData, get_domain_data
from custom_components.perific.const import DOMAIN

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


def test_domain_data_uses_one_shared_sample_store(hass: HomeAssistant) -> None:
    first = get_domain_data(hass)
    second = get_domain_data(hass)

    assert first is second
    assert first.sample_store is second.sample_store
    assert hass.data[DOMAIN] == first


def test_domain_data_replaces_unexpected_domain_state(hass: HomeAssistant) -> None:
    hass.data[DOMAIN] = {}

    domain_data = get_domain_data(hass)

    assert isinstance(domain_data, PerificDomainData)
    assert hass.data[DOMAIN] == domain_data
