# Perific for Home Assistant

Home Assistant custom integration for Perific/Enegic meters.

This repository is a clean-room community project. It is not affiliated with,
endorsed by, or supported by Perific or Enegic.

## What It Provides

- A Home Assistant UI setup flow for Perific accounts.
- Native Perific token authentication stored in the Home Assistant config entry.
- Reauthentication through Home Assistant's standard reauth flow.
- One grid power sensor per selected Perific meter.
- Cloud polling through the Perific/Enegic API.

The first supported entity is whole-home grid power in watts for local energy
management consumers such as evcc.

## Status

This integration is pre-release. The setup and grid-power sensor path has been
tested against a live Home Assistant instance, but the API is not publicly
documented by the vendor.

Use it only if you are comfortable running a custom Home Assistant integration
that depends on an undocumented cloud API.

## Requirements

- Home Assistant 2026.5.3 or newer.
- A Perific/Enegic account with at least one meter.
- Network access from Home Assistant to `https://api.enegic.com`.

## Installation

### HACS Custom Repository

1. Open HACS in Home Assistant.
2. Open custom repositories.
3. Add `https://github.com/woldner/perific-ha`.
4. Select the `Integration` category.
5. Download `Perific`.
6. Restart Home Assistant.

Use the latest GitHub Release for normal HACS installs. Use the default branch
only for controlled testing of unreleased changes.

### Manual Installation

Copy `custom_components/perific` into your Home Assistant
`custom_components` directory and restart Home Assistant.

## Setup

1. In Home Assistant, go to **Settings** -> **Devices & services**.
2. Select **Add integration**.
3. Search for **Perific**.
4. Enter your Perific email or username and password.
5. Select the meter to expose.

If your account has multiple meters, run the add integration flow again and
select another meter. Each selected meter gets its own Home Assistant config
entry and grid power sensor.

Passwords are used only during setup or reauthentication. The integration stores
the Perific token and non-secret account metadata in the Home Assistant config
entry.

## Entity Behavior

The integration creates one grid power sensor for each selected meter. For the
first meter, the default entity ID is:

- `sensor.perific_meter_grid_power`

The sensor reports net grid power in watts. It uses consecutive Perific
`PhaseMinute` import/export counter samples. It does not publish a guessed or
stale value when the required samples are missing or too old.

If the integration is working but cannot safely calculate watts yet, the sensor
state is `unknown` and `grid_power_status` explains why. If the integration
cannot fetch data or authenticate, Home Assistant marks the entity unavailable.
When fresh `PhaseMinute` data resumes, the sensor returns to numeric watts
automatically after enough consecutive samples exist to calculate a safe delta.

| State | `grid_power_status` | Meaning | Consumer behavior |
| --- | --- | --- | --- |
| Numeric watts | `ready` | A fresh grid-power value was calculated from consecutive meter samples. | Use the sensor value. |
| `unknown` | `baseline_required` | The integration has a meter sample and needs another valid sample before calculating watts. | Wait and do not substitute cached power. |
| `unknown` | `stale_phase_minute` | Perific did not provide fresh minute data. | Wait and do not use stale power. |
| `unavailable` | none or last known | The integration cannot fetch usable data or needs reauthentication. | Treat the source as offline and check logs or repairs. |

The sensor exposes diagnostic attributes:

- `grid_power_status`
- `source_timestamp`, which is also set for rejected stale packets when Perific
  provides a packet timestamp

## Troubleshooting

If setup fails:

- Confirm the same credentials work in the Perific app or web app.
- Confirm Home Assistant can reach `https://api.enegic.com`.
- Check Home Assistant logs for `custom_components.perific`.

If the sensor is `unknown`:

- Check the `grid_power_status` attribute.
- Check `source_timestamp` when `grid_power_status` is `stale_phase_minute` to
  see the rejected packet timestamp.
- Wait for the Perific meter to report fresh minute data.
- Improve meter Wi-Fi if Perific reporting is slow or intermittent.

If the sensor is unavailable:

- Confirm Home Assistant can reach `https://api.enegic.com`.
- Complete any Home Assistant reauthentication prompt for the Perific
  integration.
- Check Home Assistant logs for `custom_components.perific`.

If the API rejects the stored token, Home Assistant starts the normal
reauthentication flow. Re-enter the Perific credentials in Home Assistant; do
not edit stored tokens manually.

## API Contract

API discovery is tracked in [`api/perific.openapi.yaml`](api/perific.openapi.yaml)
and [`docs/api-verification.md`](docs/api-verification.md). These files are
clean-room project artifacts, not vendor documentation.

## Development

This project uses `uv` for the Python environment and Ruff for formatting and
linting. The default development Python is declared in `.python-version`; the
supported Python range is declared in `pyproject.toml`.

```sh
uv run python --version
uv run ruff format --check .
uv run ruff check .
uv run pytest
```

Install the local Git hooks once per clone:

```sh
uv run pre-commit install
```

Run the full local hook set before pushing or asking for review:

```sh
uv run pre-commit run --all-files
```

For changes that affect the Home Assistant config flow, coordinator, sensor
state, availability, or diagnostics, run the live smoke check when Home
Assistant access is available:

```sh
HA_URL="http://homeassistant.local:8123" HA_TOKEN="..." \
  uv run python scripts/smoke-ha-sensor.py --samples 11 --interval 60
```

The smoke check reads only `sensor.perific_meter_grid_power` from Home
Assistant. It does not call evcc and does not change charger or integration
state. Do not run it from pre-commit or CI.

For controlled live validation, you may update a Home Assistant instance
directly from the current checkout before a release. Run focused tests first
unless you are only inspecting the installed state, run the smoke check
afterward, and report the source commit or dirty diff. Do not treat this as a
HACS update or release.

Release automation is documented in [`docs/release.md`](docs/release.md).

Apply safe Ruff fixes locally with:

```sh
uv run ruff check --fix .
uv run ruff format .
```
