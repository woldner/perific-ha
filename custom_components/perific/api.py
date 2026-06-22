from __future__ import annotations

import json
import time
from dataclasses import dataclass
from json import JSONDecodeError
from typing import TYPE_CHECKING, cast

import aiohttp

from .const import CONF_PASSWORD, CONF_USERNAME, DEFAULT_API_URL

if TYPE_CHECKING:
    from collections.abc import Mapping

HTTP_MULTIPLE_CHOICES = 300
HTTP_OK = 200
HTTP_UNAUTHORIZED = 401

AUTHORIZATION_HEADER = "X-Authorization"
CONTENT_TYPE_JSON = "application/json"
MILLISECONDS_PER_SECOND = 1000
MAX_PHASE_MINUTE_PACKET_AGE_SECONDS = 300
FIELD_PHASE_MINUTE_STALE = "LatestPackets.PhaseMinute.ts.stale"
GRID_POWER_STATUS_BASELINE_REQUIRED = "baseline_required"
GRID_POWER_STATUS_READY = "ready"
GRID_POWER_STATUS_STALE_PHASE_MINUTE = "stale_phase_minute"

type JsonPrimitive = bool | int | float | str | None
type JsonValue = JsonPrimitive | list[JsonValue] | dict[str, JsonValue]
type JsonObject = dict[str, JsonValue]


class PerificError(Exception):
    """Base class for Perific API errors."""


class PerificAuthError(PerificError):
    """Perific credentials or token were rejected."""

    def __init__(self) -> None:
        super().__init__("perific_auth_failed")


class PerificConnectionError(PerificError):
    """Perific API could not be reached."""

    def __init__(self) -> None:
        super().__init__("perific_connection_failed")


class PerificResponseError(PerificError):
    """Perific API returned an unexpected HTTP response."""

    def __init__(self, status: int) -> None:
        super().__init__("perific_response_failed")
        self.status = status


class PerificDataError(PerificError):
    """Perific API returned a malformed or unsupported payload."""

    def __init__(self, field: str) -> None:
        super().__init__("perific_data_failed")
        self.field = field


@dataclass(frozen=True, slots=True)
class PerificAuth:
    token: str
    token_valid_to: str
    user_id: str


@dataclass(frozen=True, slots=True)
class PerificMeterData:
    item_id: str
    grid_power_w: float | None
    timestamp: int | None
    status: str = GRID_POWER_STATUS_READY


@dataclass(frozen=True, slots=True)
class PerificMeterSample:
    item_id: str
    import_energy_kwh: float
    export_energy_kwh: float
    timestamp: int


class PerificClient:
    def __init__(
        self,
        session: aiohttp.ClientSession,
        *,
        token: str | None = None,
        base_url: str = DEFAULT_API_URL,
    ) -> None:
        self._session = session
        self._token = token
        self._base_url = base_url.removesuffix("/")

    async def async_authenticate(self, username: str, password: str) -> PerificAuth:
        payload = await self._request(
            "PUT",
            "/createtoken",
            json_body={CONF_USERNAME: username, CONF_PASSWORD: password},
            token=None,
        )
        auth = parse_auth_response(payload)
        self._token = auth.token
        return auth

    async def async_get_account_overview(self) -> JsonValue:
        return await self._request("GET", "/getaccountoverview", token=self._token)

    async def async_get_latest_meter_sample(
        self,
        *,
        item_id: str | None = None,
        max_age_seconds: int | None = MAX_PHASE_MINUTE_PACKET_AGE_SECONDS,
    ) -> PerificMeterSample:
        payload = await self._request(
            "PUT",
            "/getlatestpackets",
            json_body={},
            token=self._token,
        )
        return parse_latest_meter_sample(
            payload,
            item_id=item_id,
            max_age_seconds=max_age_seconds,
            now_ms=int(time.time() * MILLISECONDS_PER_SECOND),
        )

    async def async_get_latest_meter_samples(
        self,
        *,
        max_age_seconds: int | None = MAX_PHASE_MINUTE_PACKET_AGE_SECONDS,
    ) -> tuple[PerificMeterSample, ...]:
        payload = await self._request(
            "PUT",
            "/getlatestpackets",
            json_body={},
            token=self._token,
        )
        return parse_latest_meter_samples(
            payload,
            max_age_seconds=max_age_seconds,
            now_ms=int(time.time() * MILLISECONDS_PER_SECOND),
        )

    async def _request(
        self,
        method: str,
        path: str,
        *,
        token: str | None,
        json_body: JsonObject | None = None,
    ) -> JsonValue:
        headers = {
            "Accept": CONTENT_TYPE_JSON,
            "Content-Type": CONTENT_TYPE_JSON,
        }
        if token is not None:
            headers[AUTHORIZATION_HEADER] = token

        try:
            async with self._session.request(
                method,
                f"{self._base_url}{path}",
                headers=headers,
                json=json_body,
            ) as response:
                if response.status == HTTP_UNAUTHORIZED:
                    raise PerificAuthError
                if not HTTP_OK <= response.status < HTTP_MULTIPLE_CHOICES:
                    raise PerificResponseError(response.status)
                return _load_json(await response.text())
        except aiohttp.ClientError as err:
            raise PerificConnectionError from err
        except TimeoutError as err:
            raise PerificConnectionError from err


def parse_auth_response(payload: JsonValue) -> PerificAuth:
    root = _require_object(payload, "root")
    token_info = _require_object(root.get("TokenInfo"), "TokenInfo")
    user = _require_object(root.get("User"), "User")

    return PerificAuth(
        token=_require_string(token_info.get("Token"), "TokenInfo.Token"),
        token_valid_to=_require_string(token_info.get("ValidTo"), "TokenInfo.ValidTo"),
        user_id=_require_identifier(user.get("UserId"), "User.UserId"),
    )


def parse_latest_meter_sample(
    payload: JsonValue,
    *,
    item_id: str | None = None,
    max_age_seconds: int | None = None,
    now_ms: int | None = None,
) -> PerificMeterSample:
    packets = _require_list(payload, "root")
    packet = _select_packet(packets, item_id)
    return _parse_meter_packet(
        packet,
        max_age_seconds=max_age_seconds,
        now_ms=now_ms,
    )


def parse_latest_meter_samples(
    payload: JsonValue,
    *,
    max_age_seconds: int | None = None,
    now_ms: int | None = None,
) -> tuple[PerificMeterSample, ...]:
    packets = _require_list(payload, "root")
    return tuple(
        _parse_meter_packet(
            _require_object(packet, f"root[{index}]"),
            max_age_seconds=max_age_seconds,
            now_ms=now_ms,
        )
        for index, packet in enumerate(packets)
    )


def _parse_meter_packet(
    packet: Mapping[str, JsonValue],
    *,
    max_age_seconds: int | None,
    now_ms: int | None,
) -> PerificMeterSample:
    latest_packets = _require_object(packet.get("LatestPackets"), "LatestPackets")
    phase_minute = _require_object(
        latest_packets.get("PhaseMinute"),
        "LatestPackets.PhaseMinute",
    )
    data = _require_object(
        phase_minute.get("data"),
        "LatestPackets.PhaseMinute.data",
    )

    import_energy_kwh = _require_number(
        data.get("hwi"),
        "LatestPackets.PhaseMinute.data.hwi",
    )
    export_energy_kwh = _require_number(
        data.get("hwo"),
        "LatestPackets.PhaseMinute.data.hwo",
    )

    timestamp = _require_int(
        phase_minute.get("ts"),
        "LatestPackets.PhaseMinute.ts",
    )
    _raise_if_stale(
        timestamp,
        now_ms=now_ms,
        max_age_seconds=max_age_seconds,
    )

    return PerificMeterSample(
        item_id=_require_identifier(packet.get("ItemId"), "ItemId"),
        import_energy_kwh=import_energy_kwh,
        export_energy_kwh=export_energy_kwh,
        timestamp=timestamp,
    )


def _select_packet(
    packets: list[JsonValue],
    item_id: str | None,
) -> Mapping[str, JsonValue]:
    if item_id is None:
        if len(packets) != 1:
            field = "ItemId.ambiguous"
            raise PerificDataError(field)
        packet = _require_object(packets[0], "root[0]")
        _require_identifier(packet.get("ItemId"), "ItemId")
        return packet

    for index, candidate in enumerate(packets):
        packet = _require_object(candidate, f"root[{index}]")
        packet_item_id = _require_identifier(packet.get("ItemId"), "ItemId")
        if packet_item_id == item_id:
            return packet
    field = "ItemId"
    raise PerificDataError(field)


def _load_json(text: str) -> JsonValue:
    try:
        return cast("JsonValue", json.loads(text))
    except JSONDecodeError as err:
        field = "response_json"
        raise PerificDataError(field) from err


def _require_object(value: JsonValue | None, field: str) -> Mapping[str, JsonValue]:
    if not isinstance(value, dict):
        raise PerificDataError(field)
    return value


def _require_list(value: JsonValue, field: str) -> list[JsonValue]:
    if not isinstance(value, list) or not value:
        raise PerificDataError(field)
    return value


def _require_string(value: JsonValue | None, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise PerificDataError(field)
    return value


def _require_identifier(value: JsonValue | None, field: str) -> str:
    if isinstance(value, bool) or value is None:
        raise PerificDataError(field)
    if isinstance(value, int | str):
        identifier = str(value)
        if identifier:
            return identifier
    raise PerificDataError(field)


def _require_number(value: JsonValue | None, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise PerificDataError(field)
    return float(value)


def _require_int(value: JsonValue | None, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise PerificDataError(field)
    return value


def _raise_if_stale(
    timestamp_ms: int,
    *,
    now_ms: int | None,
    max_age_seconds: int | None,
) -> None:
    if now_ms is None or max_age_seconds is None:
        return
    max_age_ms = max_age_seconds * MILLISECONDS_PER_SECOND
    if timestamp_ms > now_ms + max_age_ms or now_ms - timestamp_ms > max_age_ms:
        raise PerificDataError(FIELD_PHASE_MINUTE_STALE)
