# perific-ha

Home Assistant custom integration for Perific/Enegic meters.

Status: early clean-room project. This repository is not affiliated with,
endorsed by, or supported by Perific or Enegic.

## Goal

Expose Perific meter data in Home Assistant with clear units and reliable
unavailable-state behavior. The first target is whole-home grid power in watts
for local energy management use cases such as evcc.

## Scope

- Home Assistant custom integration domain: `perific`
- Integration path: `custom_components/perific`
- Authentication through the Perific/Enegic API
- Device and sensor entities for meter telemetry
- Tests built from redacted fixtures

## Current State

The repository contains the first Home Assistant integration slice: config
flow, native Perific token exchange, config-entry reauth, coordinated polling,
and one grid power sensor. The integration is still pre-release while the API
contract and meter field meanings are verified against live or vendor evidence.

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
