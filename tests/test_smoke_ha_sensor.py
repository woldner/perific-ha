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


def ready_reading(smoke: ModuleType, *, state: str) -> object:
    return smoke.BinarySensorReading(
        last_changed="2026-06-23T10:00:00+00:00",
        last_updated="2026-06-23T10:00:00+00:00",
        state=state,
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
    assert result.is_ready


def test_sample_classifier_requires_ready_binary_for_ready_state() -> None:
    smoke = load_smoke_module()

    source = reading(state="123.4", grid_power_status="ready")
    ready = smoke.classify_sample(source, ready_reading(smoke, state="on"))
    mismatched = smoke.classify_sample(source, ready_reading(smoke, state="off"))

    assert ready.is_ok
    assert ready.is_ready
    assert ready.ready_entity_matches
    assert not mismatched.is_ok
    assert not mismatched.is_ready
    assert not mismatched.ready_entity_matches
    assert not smoke.smoke_succeeds([mismatched], require_ready=True)


def test_sample_classifier_requires_waiting_binary_for_waiting_state() -> None:
    smoke = load_smoke_module()

    source = reading(state="unknown", grid_power_status="baseline_required")
    waiting = smoke.classify_sample(source, ready_reading(smoke, state="off"))
    mismatched = smoke.classify_sample(source, ready_reading(smoke, state="on"))

    assert waiting.is_ok
    assert not waiting.is_ready
    assert waiting.ready_entity_matches
    assert not mismatched.is_ok
    assert not mismatched.is_ready
    assert not mismatched.ready_entity_matches
    assert not smoke.smoke_succeeds([mismatched], require_ready=False)


def test_classifier_rejects_numeric_state_without_ready_status() -> None:
    smoke = load_smoke_module()

    result = smoke.classify_reading(
        reading(state="123.4", grid_power_status=None, source_timestamp=None),
    )

    assert not result.is_ok
    assert not result.is_ready


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
    assert not baseline.is_ready
    assert not stale.is_ready


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


def test_contract_smoke_can_pass_with_expected_waiting_state() -> None:
    smoke = load_smoke_module()

    classifications = [
        smoke.classify_reading(
            reading(state="unknown", grid_power_status="baseline_required"),
        ),
    ]

    assert smoke.smoke_succeeds(classifications, require_ready=False)


def test_custom_grid_entity_requires_explicit_ready_entity() -> None:
    smoke = load_smoke_module()
    args = smoke.argparse.Namespace(
        grid_power_entity_id="sensor.custom_grid_power",
        ha_url="http://homeassistant.local:8123",
        interval=0,
        ready_entity_id=None,
        samples=1,
        token="token",
    )

    assert (
        smoke.validate_args(args)
        == "--ready-entity-id is required when --grid-power-entity-id is customized"
    )


def test_readiness_smoke_requires_numeric_ready_state() -> None:
    smoke = load_smoke_module()

    waiting = smoke.classify_reading(
        reading(state="unknown", grid_power_status="baseline_required"),
    )
    ready = smoke.classify_reading(
        reading(state="123.4", grid_power_status="ready"),
    )

    assert not smoke.smoke_succeeds([waiting], require_ready=True)
    assert smoke.smoke_succeeds([waiting, ready], require_ready=True)


def test_readiness_smoke_requires_final_sample_to_be_ready() -> None:
    smoke = load_smoke_module()

    ready = smoke.classify_reading(
        reading(state="123.4", grid_power_status="ready"),
    )
    stale = smoke.classify_reading(
        reading(state="unknown", grid_power_status="stale_phase_minute"),
    )

    assert not smoke.smoke_succeeds([ready, stale], require_ready=True)


def test_readiness_summary_reports_current_ready_state() -> None:
    smoke = load_smoke_module()

    ready = smoke.classify_reading(
        reading(state="123.4", grid_power_status="ready"),
    )
    stale = smoke.classify_reading(
        reading(state="unknown", grid_power_status="stale_phase_minute"),
    )

    assert smoke.smoke_summary([ready, stale], require_ready=True) == {
        "evcc_ready": False,
        "ready_samples": 1,
        "ready_mismatch_samples": 0,
        "require_ready": True,
        "samples": 2,
        "smoke_passed": False,
        "summary": "smoke_result",
    }
