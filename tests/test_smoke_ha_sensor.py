"""Tests for the live Home Assistant smoke check classifier."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from types import ModuleType

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "smoke-ha-sensor.py"


def load_smoke_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("smoke_ha_sensor", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def reading(
    *,
    state: str,
    grid_power_status: str | None,
    source_timestamp: int | None = 1782209340000,
    unit_of_measurement: str | None = "W",
) -> object:
    smoke = load_smoke_module()
    return smoke.SensorReading(
        grid_power_status=grid_power_status,
        last_changed="2026-06-23T10:00:00+00:00",
        last_updated="2026-06-23T10:00:00+00:00",
        source_timestamp=source_timestamp,
        state=state,
        unit_of_measurement=unit_of_measurement,
    )


def test_classifier_accepts_numeric_state() -> None:
    smoke = load_smoke_module()

    result = smoke.classify_reading(
        reading(
            state="123.4",
            grid_power_status="ready",
            source_timestamp=None,
        ),
    )

    assert result.is_ok


def test_classifier_rejects_numeric_state_without_ready_status() -> None:
    smoke = load_smoke_module()

    result = smoke.classify_reading(
        reading(state="123.4", grid_power_status=None, source_timestamp=None),
    )

    assert not result.is_ok


def test_classifier_accepts_expected_unknown_states_with_timestamps() -> None:
    smoke = load_smoke_module()

    baseline = smoke.classify_reading(
        reading(state="unknown", grid_power_status="baseline_required"),
    )
    stale = smoke.classify_reading(
        reading(state="unknown", grid_power_status="stale_phase_minute"),
    )

    assert baseline.is_ok
    assert stale.is_ok


def test_classifier_rejects_unavailable_state() -> None:
    smoke = load_smoke_module()

    result = smoke.classify_reading(
        reading(
            state="unavailable",
            grid_power_status=None,
            source_timestamp=None,
        ),
    )

    assert not result.is_ok


def test_classifier_rejects_non_watt_unit() -> None:
    smoke = load_smoke_module()

    result = smoke.classify_reading(
        reading(state="123.4", grid_power_status=None, unit_of_measurement="kW"),
    )

    assert not result.is_ok


def test_classifier_rejects_unknown_without_status() -> None:
    smoke = load_smoke_module()

    result = smoke.classify_reading(
        reading(state="unknown", grid_power_status=None),
    )

    assert not result.is_ok


def test_classifier_accepts_expected_unknown_without_timestamp() -> None:
    smoke = load_smoke_module()

    result = smoke.classify_reading(
        reading(
            state="unknown",
            grid_power_status="baseline_required",
            source_timestamp=None,
        ),
    )

    assert result.is_ok
