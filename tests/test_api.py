from __future__ import annotations

import pytest

from custom_components.perific.api import (
    PerificAuth,
    PerificDataError,
    PerificMeterData,
    parse_auth_response,
    parse_latest_meter_data,
)


def test_parse_auth_response() -> None:
    payload = {
        "TokenInfo": {
            "Token": "redacted-token",
            "ValidTo": "2027-06-22T00:00:00",
        },
        "User": {"UserId": 12345},
    }

    assert parse_auth_response(payload) == PerificAuth(
        token="redacted-token",
        token_valid_to="2027-06-22T00:00:00",
        user_id="12345",
    )


def test_parse_latest_meter_data_uses_minute_import_export_watts() -> None:
    payload = [
        {
            "ItemId": 67890,
            "LatestPackets": {
                "PhaseMinute": {
                    "data": {
                        "hwi": 3120.5,
                        "hwo": 120,
                    },
                    "ts": 1782120000,
                },
            },
        },
    ]

    assert parse_latest_meter_data(payload) == PerificMeterData(
        item_id="67890",
        grid_power_w=3000.5,
        timestamp=1782120000,
    )


def test_parse_latest_meter_data_selects_configured_item_id() -> None:
    payload = [
        {
            "ItemId": 11111,
            "LatestPackets": {
                "PhaseMinute": {
                    "data": {
                        "hwi": 1000,
                        "hwo": 0,
                    },
                    "ts": 1782120000,
                },
            },
        },
        {
            "ItemId": 22222,
            "LatestPackets": {
                "PhaseMinute": {
                    "data": {
                        "hwi": 3000,
                        "hwo": 250,
                    },
                    "ts": 1782120060,
                },
            },
        },
    ]

    assert parse_latest_meter_data(payload, item_id="22222") == PerificMeterData(
        item_id="22222",
        grid_power_w=2750.0,
        timestamp=1782120060,
    )


def test_parse_latest_meter_data_rejects_missing_watt_fields() -> None:
    payload = [
        {
            "ItemId": 67890,
            "LatestPackets": {
                "PhaseMinute": {
                    "data": {
                        "hiavg": [1.0, 2.0, 3.0],
                        "huavg": [230.0, 231.0, 232.0],
                    },
                    "ts": 1782120000,
                },
            },
        },
    ]

    with pytest.raises(PerificDataError):
        parse_latest_meter_data(payload)
