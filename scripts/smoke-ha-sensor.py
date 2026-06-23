#!/usr/bin/env python3
"""Read the Perific grid-power entity from a live Home Assistant instance."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any

DEFAULT_ENTITY_ID = "sensor.perific_meter_grid_power"
DEFAULT_INTERVAL_SECONDS = 60
DEFAULT_SAMPLES = 1
DEFAULT_TIMEOUT_SECONDS = 10
EXIT_FAILURE = 2
EXIT_USAGE = 64
HTTP_NOT_FOUND = 404
HTTP_UNAUTHORIZED = 401
EXPECTED_UNKNOWN_STATUSES = frozenset({"baseline_required", "stale_phase_minute"})
EXPECTED_UNIT_OF_MEASUREMENT = "W"
READY_STATUS = "ready"
STATE_UNKNOWN = "unknown"
STATE_UNAVAILABLE = "unavailable"


class SmokeCheckError(Exception):
    """Raised when the live Home Assistant smoke check cannot run."""


@dataclass(frozen=True, slots=True)
class SensorReading:
    state: str
    grid_power_status: str | None
    source_timestamp: int | None
    last_changed: str | None
    last_updated: str | None
    unit_of_measurement: str | None

    def to_output(self) -> dict[str, object]:
        return {
            "classification": classify_reading(self).classification,
            "grid_power_status": self.grid_power_status,
            "last_changed": self.last_changed,
            "last_updated": self.last_updated,
            "source_timestamp": self.source_timestamp,
            "source_timestamp_age_seconds": source_timestamp_age_seconds(self),
            "state": self.state,
            "unit_of_measurement": self.unit_of_measurement,
        }


@dataclass(frozen=True, slots=True)
class Classification:
    classification: str
    is_ok: bool
    is_ready: bool = False


def classify_reading(reading: SensorReading) -> Classification:
    classification = "unexpected_state"
    is_ok = False
    is_ready = False

    if reading.unit_of_measurement != EXPECTED_UNIT_OF_MEASUREMENT:
        classification = "missing_watt_unit"
    elif reading.state == STATE_UNAVAILABLE:
        classification = "unavailable"
    elif reading.state == STATE_UNKNOWN:
        if reading.grid_power_status in EXPECTED_UNKNOWN_STATUSES:
            classification = reading.grid_power_status
            is_ok = True
        else:
            classification = "unknown_missing_grid_power_status"
    elif _is_number(reading.state):
        if reading.grid_power_status == READY_STATUS:
            classification = READY_STATUS
            is_ok = True
            is_ready = True
        else:
            classification = "numeric_missing_ready_status"

    return Classification(
        classification=classification,
        is_ok=is_ok,
        is_ready=is_ready,
    )


def smoke_succeeds(
    classifications: list[Classification],
    *,
    require_ready: bool,
) -> bool:
    if not classifications:
        return False
    if not all(classification.is_ok for classification in classifications):
        return False
    return not require_ready or classifications[-1].is_ready


def smoke_summary(
    classifications: list[Classification],
    *,
    require_ready: bool,
) -> dict[str, object]:
    ready_samples = sum(classification.is_ready for classification in classifications)
    current_ready = classifications[-1].is_ready if classifications else False
    return {
        "evcc_ready": current_ready,
        "ready_samples": ready_samples,
        "require_ready": require_ready,
        "samples": len(classifications),
        "smoke_passed": smoke_succeeds(
            classifications,
            require_ready=require_ready,
        ),
        "summary": "smoke_result",
    }


def source_timestamp_age_seconds(reading: SensorReading) -> int | None:
    if reading.source_timestamp is None:
        return None
    return max(0, int(time.time() - reading.source_timestamp / 1000))


def reading_from_state_payload(payload: dict[str, Any]) -> SensorReading:
    attributes = payload.get("attributes")
    if not isinstance(attributes, dict):
        attributes = {}

    return SensorReading(
        state=str(payload.get("state", "")),
        grid_power_status=_optional_string(attributes.get("grid_power_status")),
        source_timestamp=_optional_int(attributes.get("source_timestamp")),
        last_changed=_optional_string(payload.get("last_changed")),
        last_updated=_optional_string(payload.get("last_updated")),
        unit_of_measurement=_optional_string(attributes.get("unit_of_measurement")),
    )


def build_url(ha_url: str, entity_id: str) -> str:
    encoded_entity_id = urllib.parse.quote(entity_id, safe="")
    return f"{ha_url.rstrip('/')}/api/states/{encoded_entity_id}"


def fetch_reading(
    *,
    ha_url: str,
    token: str,
    entity_id: str,
    timeout: int,
) -> SensorReading:
    parsed_url = urllib.parse.urlparse(ha_url)
    if parsed_url.scheme not in {"http", "https"}:
        msg = "HA_URL must use http or https"
        raise SmokeCheckError(msg)

    request = urllib.request.Request(  # noqa: S310
        build_url(ha_url, entity_id),
        headers={
            "Accept": "application/json",
            "Authorization": f"Bearer {token}",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
            payload = json.load(response)
    except urllib.error.HTTPError as err:
        if err.code == HTTP_UNAUTHORIZED:
            msg = "Home Assistant rejected HA_TOKEN"
            raise SmokeCheckError(msg) from err
        if err.code == HTTP_NOT_FOUND:
            msg = f"Home Assistant entity not found: {entity_id}"
            raise SmokeCheckError(msg) from err
        msg = f"Home Assistant returned HTTP {err.code}"
        raise SmokeCheckError(msg) from err
    except urllib.error.URLError as err:
        msg = f"could not reach Home Assistant: {err.reason}"
        raise SmokeCheckError(msg) from err

    if not isinstance(payload, dict):
        msg = "Home Assistant returned a non-object state payload"
        raise SmokeCheckError(msg)
    return reading_from_state_payload(payload)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Poll sensor.perific_meter_grid_power from Home Assistant and "
            "classify the Perific sensor contract."
        ),
    )
    parser.add_argument("--ha-url", default=os.environ.get("HA_URL"))
    parser.add_argument("--token", default=os.environ.get("HA_TOKEN"))
    parser.add_argument("--entity-id", default=DEFAULT_ENTITY_ID)
    parser.add_argument("--samples", type=int, default=DEFAULT_SAMPLES)
    parser.add_argument("--interval", type=int, default=DEFAULT_INTERVAL_SECONDS)
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument(
        "--require-ready",
        action="store_true",
        help="Fail unless the final sample is numeric watts with status ready.",
    )
    return parser.parse_args()


def validate_args(args: argparse.Namespace) -> str | None:
    if not args.ha_url:
        return "HA_URL or --ha-url is required"
    if not args.token:
        return "HA_TOKEN or --token is required"
    if args.samples < 1:
        return "--samples must be at least 1"
    if args.interval < 0:
        return "--interval must be 0 or greater"
    return None


def main() -> int:
    args = parse_args()
    validation_error = validate_args(args)
    if validation_error is not None:
        sys.stderr.write(f"{validation_error}\n")
        return EXIT_USAGE

    classifications: list[Classification] = []
    for index in range(args.samples):
        try:
            reading = fetch_reading(
                ha_url=args.ha_url,
                token=args.token,
                entity_id=args.entity_id,
                timeout=args.timeout,
            )
        except SmokeCheckError as err:
            sys.stderr.write(f"{err}\n")
            return EXIT_FAILURE

        classification = classify_reading(reading)
        classifications.append(classification)
        output = {
            "evcc_ready": classification.is_ready,
            "sample": index + 1,
            **reading.to_output(),
        }
        sys.stdout.write(f"{json.dumps(output, sort_keys=True)}\n")
        if not classification.is_ok:
            return EXIT_FAILURE
        if index + 1 < args.samples:
            time.sleep(args.interval)

    summary = smoke_summary(classifications, require_ready=args.require_ready)
    sys.stdout.write(f"{json.dumps(summary, sort_keys=True)}\n")
    return 0 if bool(summary["smoke_passed"]) else EXIT_FAILURE


def _is_number(value: str) -> bool:
    try:
        float(value)
    except ValueError:
        return False
    return True


def _optional_string(value: object) -> str | None:
    if value is None:
        return None
    return str(value)


def _optional_int(value: object) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except TypeError, ValueError:
        return None


if __name__ == "__main__":
    raise SystemExit(main())
