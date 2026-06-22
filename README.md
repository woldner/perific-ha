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

- Home Assistant 2026.6.4 or newer.
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

Until the first public GitHub release exists, install from the default branch
for controlled testing. Public distribution should use GitHub releases so HACS
can show normal version choices.

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

The sensor may be unavailable while the integration waits for a fresh baseline,
after a long reporting gap, or when the Perific cloud API does not provide fresh
minute data. This is intentional: unavailable is safer than stale power for
energy management.

The sensor exposes diagnostic attributes:

- `grid_power_status`
- `source_timestamp`

## Troubleshooting

If setup fails:

- Confirm the same credentials work in the Perific app or web app.
- Confirm Home Assistant can reach `https://api.enegic.com`.
- Check Home Assistant logs for `custom_components.perific`.

If the sensor is unavailable:

- Check the `grid_power_status` attribute.
- Wait for the Perific meter to report fresh minute data.
- Improve meter Wi-Fi if Perific reporting is slow or intermittent.

If the API rejects the stored token, Home Assistant starts the normal
reauthentication flow.

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

Apply safe Ruff fixes locally with:

```sh
uv run ruff check --fix .
uv run ruff format .
```
