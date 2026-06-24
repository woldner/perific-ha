from __future__ import annotations

from dataclasses import dataclass

from .api import (
    MAX_PHASE_MINUTE_PACKET_AGE_SECONDS,
    MILLISECONDS_PER_SECOND,
    PerificDataError,
    PerificMeterData,
    PerificMeterSample,
)

MILLISECONDS_PER_HOUR = 60 * 60 * MILLISECONDS_PER_SECOND
WATT_HOURS_PER_KILOWATT_HOUR = 1000
MAX_POWER_DELTA_SECONDS = MAX_PHASE_MINUTE_PACKET_AGE_SECONDS
FIELD_COUNTER_DECREASED = "LatestPackets.PhaseMinute.data"
FIELD_SAMPLE_WINDOW_EXCEEDED = "LatestPackets.PhaseMinute.ts.elapsed"


@dataclass(slots=True)
class PerificGridPowerAccumulator:
    counter_reset_candidate: PerificMeterSample | None = None
    last_data: PerificMeterData | None = None
    last_sample: PerificMeterSample | None = None

    def update(
        self,
        sample: PerificMeterSample,
    ) -> PerificMeterData | None:
        if self.last_sample is None:
            return self._reset_baseline(sample)

        if sample.timestamp == self.last_sample.timestamp:
            return self._reset_baseline(sample)

        try:
            return self._publish_delta(self.last_sample, sample)
        except PerificDataError as err:
            if err.field == FIELD_SAMPLE_WINDOW_EXCEEDED:
                return self._reset_baseline(sample)
            if err.field == FIELD_COUNTER_DECREASED:
                return self._handle_counter_decrease(sample)
            raise

    def _handle_counter_decrease(
        self,
        sample: PerificMeterSample,
    ) -> PerificMeterData | None:
        if self.counter_reset_candidate is not None:
            if sample.timestamp == self.counter_reset_candidate.timestamp:
                return None
            try:
                return self._publish_delta(self.counter_reset_candidate, sample)
            except PerificDataError as err:
                if err.field != FIELD_COUNTER_DECREASED:
                    raise

        self.counter_reset_candidate = sample
        self.last_data = None
        return None

    def _publish_delta(
        self,
        previous: PerificMeterSample,
        sample: PerificMeterSample,
    ) -> PerificMeterData:
        grid_power_w = calculate_grid_power_w(
            previous,
            sample,
            max_elapsed_seconds=MAX_POWER_DELTA_SECONDS,
        )
        self.counter_reset_candidate = None
        self.last_sample = sample
        self.last_data = PerificMeterData(
            item_id=sample.item_id,
            grid_power_w=grid_power_w,
            timestamp=sample.timestamp,
        )
        return self.last_data

    def _reset_baseline(self, sample: PerificMeterSample) -> None:
        self.counter_reset_candidate = None
        self.last_sample = sample
        self.last_data = None


def calculate_grid_power_w(
    previous: PerificMeterSample,
    current: PerificMeterSample,
    *,
    max_elapsed_seconds: int | None = MAX_POWER_DELTA_SECONDS,
) -> float:
    if current.item_id != previous.item_id:
        field = "ItemId"
        raise PerificDataError(field)
    elapsed_ms = current.timestamp - previous.timestamp
    if elapsed_ms <= 0:
        field = "LatestPackets.PhaseMinute.ts"
        raise PerificDataError(field)
    if (
        max_elapsed_seconds is not None
        and elapsed_ms > max_elapsed_seconds * MILLISECONDS_PER_SECOND
    ):
        raise PerificDataError(FIELD_SAMPLE_WINDOW_EXCEEDED)

    import_delta = current.import_energy_kwh - previous.import_energy_kwh
    export_delta = current.export_energy_kwh - previous.export_energy_kwh
    if import_delta < 0 or export_delta < 0:
        raise PerificDataError(FIELD_COUNTER_DECREASED)

    net_delta_kwh = import_delta - export_delta
    return (
        net_delta_kwh
        * WATT_HOURS_PER_KILOWATT_HOUR
        * MILLISECONDS_PER_HOUR
        / elapsed_ms
    )
