from __future__ import annotations

import pytest

from custom_components.perific.api import (
    PerificAuth,
    PerificDataError,
    PerificMeterData,
    PerificMeterSample,
    parse_auth_response,
    parse_latest_meter_sample,
    parse_latest_meter_samples,
)
from custom_components.perific.meter import (
    PerificGridPowerAccumulator,
    calculate_grid_power_w,
)

FIRST_SAMPLE_TIMESTAMP = 1782120000000
SECOND_SAMPLE_TIMESTAMP = 1782120060000
STALE_SAMPLE_TIMESTAMP = FIRST_SAMPLE_TIMESTAMP


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


def test_parse_latest_meter_sample_reads_minute_energy_counters() -> None:
    payload = [
        {
            "ItemId": 67890,
            "LatestPackets": {
                "PhaseRealTime": {
                    "data": {
                        "hiavg": [10.0, 5.0, 2.5],
                        "huavg": [230.0, 231.0, 232.0],
                    },
                    "ts": FIRST_SAMPLE_TIMESTAMP,
                },
                "PhaseMinute": {
                    "data": {
                        "hwi": 3120.5,
                        "hwo": 120,
                    },
                    "ts": FIRST_SAMPLE_TIMESTAMP,
                },
            },
        },
    ]

    assert parse_latest_meter_sample(payload) == PerificMeterSample(
        item_id="67890",
        import_energy_kwh=3120.5,
        export_energy_kwh=120.0,
        timestamp=FIRST_SAMPLE_TIMESTAMP,
    )


def test_parse_latest_meter_sample_selects_configured_item_id() -> None:
    payload = [
        {
            "ItemId": 11111,
            "LatestPackets": {
                "PhaseMinute": {
                    "data": {
                        "hwi": 1000,
                        "hwo": 10,
                    },
                    "ts": 1782120000000,
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
                    "ts": 1782120060000,
                },
            },
        },
    ]

    assert parse_latest_meter_sample(payload, item_id="22222") == PerificMeterSample(
        item_id="22222",
        import_energy_kwh=3000.0,
        export_energy_kwh=250.0,
        timestamp=1782120060000,
    )


def test_parse_latest_meter_samples_reads_all_meter_candidates() -> None:
    payload = [
        {
            "ItemId": 11111,
            "LatestPackets": {
                "PhaseMinute": {
                    "data": {
                        "hwi": 1000,
                        "hwo": 10,
                    },
                    "ts": 1782120000000,
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
                    "ts": 1782120060000,
                },
            },
        },
    ]

    assert parse_latest_meter_samples(payload, max_age_seconds=None) == (
        PerificMeterSample(
            item_id="11111",
            import_energy_kwh=1000.0,
            export_energy_kwh=10.0,
            timestamp=1782120000000,
        ),
        PerificMeterSample(
            item_id="22222",
            import_energy_kwh=3000.0,
            export_energy_kwh=250.0,
            timestamp=1782120060000,
        ),
    )


def test_parse_latest_meter_sample_rejects_ambiguous_unconfigured_item_id() -> None:
    payload = [
        {
            "ItemId": 11111,
            "LatestPackets": {
                "PhaseMinute": {
                    "data": {
                        "hwi": 1000,
                        "hwo": 10,
                    },
                    "ts": 1782120000000,
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
                    "ts": 1782120060000,
                },
            },
        },
    ]

    with pytest.raises(PerificDataError, match="perific_data_failed") as err:
        parse_latest_meter_sample(payload)

    assert err.value.field == "ItemId.ambiguous"


def test_parse_latest_meter_sample_rejects_missing_energy_counters() -> None:
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
        parse_latest_meter_sample(payload)


def test_parse_latest_meter_sample_rejects_missing_timestamp() -> None:
    payload = [
        {
            "ItemId": 67890,
            "LatestPackets": {
                "PhaseMinute": {
                    "data": {
                        "hwi": 1000,
                        "hwo": 10,
                    },
                },
            },
        },
    ]

    with pytest.raises(PerificDataError):
        parse_latest_meter_sample(payload)


def test_parse_latest_meter_sample_rejects_stale_minute_packet() -> None:
    payload = [
        {
            "ItemId": 67890,
            "LatestPackets": {
                "PhaseMinute": {
                    "data": {
                        "hwi": 1000,
                        "hwo": 10,
                    },
                    "ts": STALE_SAMPLE_TIMESTAMP,
                },
            },
        },
    ]

    with pytest.raises(PerificDataError) as err:
        parse_latest_meter_sample(
            payload,
            max_age_seconds=120,
            now_ms=1782120121001,
        )

    assert err.value.timestamp == STALE_SAMPLE_TIMESTAMP


def test_parse_latest_meter_sample_can_ignore_freshness_for_meter_discovery() -> None:
    payload = [
        {
            "ItemId": 67890,
            "LatestPackets": {
                "PhaseMinute": {
                    "data": {
                        "hwi": 1000,
                        "hwo": 10,
                    },
                    "ts": 1782120000000,
                },
            },
        },
    ]

    assert parse_latest_meter_sample(
        payload,
        max_age_seconds=None,
        now_ms=1782129999000,
    ) == PerificMeterSample(
        item_id="67890",
        import_energy_kwh=1000.0,
        export_energy_kwh=10.0,
        timestamp=1782120000000,
    )


def test_calculate_grid_power_w_uses_energy_counter_delta() -> None:
    previous = PerificMeterSample(
        item_id="67890",
        import_energy_kwh=1000.000,
        export_energy_kwh=10.000,
        timestamp=1782120000000,
    )
    current = PerificMeterSample(
        item_id="67890",
        import_energy_kwh=1000.167,
        export_energy_kwh=10.000,
        timestamp=1782120060000,
    )

    assert calculate_grid_power_w(previous, current) == pytest.approx(10020.0)


def test_calculate_grid_power_w_subtracts_export_counter_delta() -> None:
    previous = PerificMeterSample(
        item_id="67890",
        import_energy_kwh=1000.000,
        export_energy_kwh=10.000,
        timestamp=1782120000000,
    )
    current = PerificMeterSample(
        item_id="67890",
        import_energy_kwh=1000.100,
        export_energy_kwh=10.025,
        timestamp=1782120060000,
    )

    assert calculate_grid_power_w(previous, current) == pytest.approx(4500.0)


def test_calculate_grid_power_w_reports_export_as_negative_power() -> None:
    previous = PerificMeterSample(
        item_id="67890",
        import_energy_kwh=1000.000,
        export_energy_kwh=10.000,
        timestamp=1782120000000,
    )
    current = PerificMeterSample(
        item_id="67890",
        import_energy_kwh=1000.025,
        export_energy_kwh=10.100,
        timestamp=1782120060000,
    )

    assert calculate_grid_power_w(previous, current) == pytest.approx(-4500.0)


def test_calculate_grid_power_w_rejects_non_newer_sample() -> None:
    previous = PerificMeterSample(
        item_id="67890",
        import_energy_kwh=1000.000,
        export_energy_kwh=10.000,
        timestamp=1782120000000,
    )
    current = PerificMeterSample(
        item_id="67890",
        import_energy_kwh=1000.100,
        export_energy_kwh=10.000,
        timestamp=1782120000000,
    )

    with pytest.raises(PerificDataError):
        calculate_grid_power_w(previous, current)


def test_calculate_grid_power_w_rejects_overlong_sample_window() -> None:
    previous = PerificMeterSample(
        item_id="67890",
        import_energy_kwh=1000.000,
        export_energy_kwh=10.000,
        timestamp=1782120000000,
    )
    current = PerificMeterSample(
        item_id="67890",
        import_energy_kwh=1000.500,
        export_energy_kwh=10.000,
        timestamp=1782120960001,
    )

    with pytest.raises(PerificDataError):
        calculate_grid_power_w(previous, current, max_elapsed_seconds=960)


def test_grid_power_accumulator_requires_initial_baseline() -> None:
    accumulator = PerificGridPowerAccumulator()
    first_sample = _meter_sample(
        import_energy_kwh=1000.000,
        timestamp=1782120000000,
    )

    assert accumulator.update(first_sample) is None
    assert accumulator.last_sample == first_sample
    assert accumulator.last_data is None


def test_grid_power_accumulator_uses_next_newer_sample() -> None:
    accumulator = PerificGridPowerAccumulator()

    assert (
        accumulator.update(
            _meter_sample(
                import_energy_kwh=1000.000,
                timestamp=1782120000000,
            ),
        )
        is None
    )
    data = accumulator.update(
        _meter_sample(
            import_energy_kwh=1000.167,
            timestamp=SECOND_SAMPLE_TIMESTAMP,
        ),
    )

    assert data is not None
    assert data.grid_power_w == pytest.approx(10020.0)
    assert data.timestamp == SECOND_SAMPLE_TIMESTAMP


def test_grid_power_accumulator_withholds_same_timestamp_after_ready_data() -> None:
    accumulator = PerificGridPowerAccumulator()

    assert (
        accumulator.update(
            _meter_sample(
                import_energy_kwh=1000.000,
                timestamp=1782120000000,
            ),
        )
        is None
    )
    data = accumulator.update(
        _meter_sample(
            import_energy_kwh=1000.167,
            timestamp=SECOND_SAMPLE_TIMESTAMP,
        ),
    )

    assert data is not None
    repeated_sample = _meter_sample(
        import_energy_kwh=1000.167,
        timestamp=SECOND_SAMPLE_TIMESTAMP,
    )

    assert accumulator.update(repeated_sample) is None
    assert accumulator.last_sample == repeated_sample
    assert accumulator.last_data is None


def test_grid_power_accumulator_clears_seeded_data_for_same_timestamp() -> None:
    sample = _meter_sample(
        import_energy_kwh=1000.167,
        timestamp=SECOND_SAMPLE_TIMESTAMP,
    )
    accumulator = PerificGridPowerAccumulator(
        last_data=PerificMeterData(
            item_id=sample.item_id,
            grid_power_w=10020.0,
            timestamp=sample.timestamp,
        ),
        last_sample=sample,
    )

    assert accumulator.update(sample) is None
    assert accumulator.last_sample == sample
    assert accumulator.last_data is None


def test_grid_power_accumulator_does_not_publish_repeated_first_sample() -> None:
    accumulator = PerificGridPowerAccumulator()

    assert (
        accumulator.update(
            _meter_sample(
                import_energy_kwh=1000.000,
                timestamp=1782120000000,
            ),
        )
        is None
    )
    assert (
        accumulator.update(
            _meter_sample(
                import_energy_kwh=1000.000,
                timestamp=1782120000000,
            ),
        )
        is None
    )


def test_grid_power_accumulator_resets_baseline_after_overlong_gap() -> None:
    accumulator = PerificGridPowerAccumulator()
    delayed_sample = _meter_sample(
        import_energy_kwh=1000.500,
        timestamp=1782120960001,
    )

    assert (
        accumulator.update(
            _meter_sample(
                import_energy_kwh=1000.000,
                timestamp=1782120000000,
            ),
        )
        is None
    )
    assert accumulator.update(delayed_sample) is None

    assert accumulator.last_sample == delayed_sample
    assert accumulator.last_data is None


def test_grid_power_accumulator_keeps_baseline_after_out_of_order_sample() -> None:
    accumulator = PerificGridPowerAccumulator()
    baseline = _meter_sample(
        import_energy_kwh=1000.000,
        timestamp=1782120000000,
    )
    out_of_order_sample = _meter_sample(
        import_energy_kwh=999.900,
        timestamp=1782119940000,
    )

    assert accumulator.update(baseline) is None
    with pytest.raises(PerificDataError):
        accumulator.update(out_of_order_sample)

    assert accumulator.last_sample == baseline
    assert accumulator.last_data is None


def test_grid_power_accumulator_confirms_counter_reset_before_publishing() -> None:
    accumulator = PerificGridPowerAccumulator()
    baseline = _meter_sample(
        import_energy_kwh=1000.000,
        timestamp=1782120000000,
    )
    reset_candidate = _meter_sample(
        import_energy_kwh=0.001,
        timestamp=1782120060000,
    )
    confirmed_reset = _meter_sample(
        import_energy_kwh=0.168,
        timestamp=1782120120000,
    )

    assert accumulator.update(baseline) is None
    assert accumulator.update(reset_candidate) is None

    data = accumulator.update(confirmed_reset)

    assert data is not None
    assert data.grid_power_w == pytest.approx(10020.0)
    assert accumulator.counter_reset_candidate is None
    assert accumulator.last_sample == confirmed_reset


def test_grid_power_accumulator_rejects_out_of_order_reset_candidate() -> None:
    accumulator = PerificGridPowerAccumulator()
    baseline = _meter_sample(
        import_energy_kwh=1000.000,
        timestamp=1782120000000,
    )
    reset_candidate = _meter_sample(
        import_energy_kwh=0.001,
        timestamp=1782120060000,
    )
    out_of_order_candidate = _meter_sample(
        import_energy_kwh=0.002,
        timestamp=1782120030000,
    )

    assert accumulator.update(baseline) is None
    assert accumulator.update(reset_candidate) is None
    with pytest.raises(PerificDataError) as err:
        accumulator.update(out_of_order_candidate)

    assert err.value.field == "LatestPackets.PhaseMinute.ts"
    assert accumulator.counter_reset_candidate == reset_candidate
    assert accumulator.last_sample == baseline
    assert accumulator.last_data is None


def test_grid_power_accumulator_keeps_duplicate_reset_candidate_waiting() -> None:
    accumulator = PerificGridPowerAccumulator()
    baseline = _meter_sample(
        import_energy_kwh=1000.000,
        timestamp=1782120000000,
    )
    reset_candidate = _meter_sample(
        import_energy_kwh=0.001,
        timestamp=1782120060000,
    )

    assert accumulator.update(baseline) is None
    assert accumulator.update(reset_candidate) is None
    assert accumulator.update(reset_candidate) is None

    assert accumulator.counter_reset_candidate == reset_candidate
    assert accumulator.last_sample == baseline
    assert accumulator.last_data is None


def test_grid_power_accumulator_ignores_reset_candidate_on_old_series_resume() -> None:
    accumulator = PerificGridPowerAccumulator()
    baseline = _meter_sample(
        import_energy_kwh=1000.000,
        timestamp=1782120000000,
    )
    reset_candidate = _meter_sample(
        import_energy_kwh=900.000,
        timestamp=1782120060000,
    )
    resumed_sample = _meter_sample(
        import_energy_kwh=1000.167,
        timestamp=1782120120000,
    )

    assert accumulator.update(baseline) is None
    assert accumulator.update(reset_candidate) is None

    data = accumulator.update(resumed_sample)

    assert data is not None
    assert data.grid_power_w == pytest.approx(5010.0)
    assert accumulator.counter_reset_candidate is None
    assert accumulator.last_sample == resumed_sample


def test_grid_power_accumulator_skips_ambiguous_reset_after_old_window() -> None:
    accumulator = PerificGridPowerAccumulator()
    baseline = _meter_sample(
        import_energy_kwh=1000.000,
        timestamp=1782120000000,
    )
    reset_candidate = _meter_sample(
        import_energy_kwh=900.000,
        timestamp=1782120060000,
    )
    resumed_sample = _meter_sample(
        import_energy_kwh=1000.167,
        timestamp=1782120300001,
    )

    assert accumulator.update(baseline) is None
    assert accumulator.update(reset_candidate) is None

    assert accumulator.update(resumed_sample) is None

    assert accumulator.counter_reset_candidate is None
    assert accumulator.last_sample == resumed_sample
    assert accumulator.last_data is None


def _meter_sample(
    *,
    import_energy_kwh: float,
    timestamp: int,
    export_energy_kwh: float = 10.0,
    item_id: str = "67890",
) -> PerificMeterSample:
    return PerificMeterSample(
        item_id=item_id,
        import_energy_kwh=import_energy_kwh,
        export_energy_kwh=export_energy_kwh,
        timestamp=timestamp,
    )
