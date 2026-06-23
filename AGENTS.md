# Agent Instructions

This repo builds a clean-room Home Assistant custom integration for
Perific/Enegic meters.

Use current Home Assistant developer docs, this repo's source, tests, fixtures,
and explicit user constraints as authority. Treat community Perific repos and
forum posts as context only.

Repo-local skills live in `.agents/skills`. When the user invokes
`$skill-name` or a task matches an available skill description, read the owning
skill before acting. Use skill descriptions as the trigger authority; update
the owning `SKILL.md` when trigger behavior is wrong instead of copying skill
workflows into this file.

Do not copy code, generated clients, OpenAPI specs, fixtures, entity mappings,
or prose from other Perific integrations unless the user explicitly approves the
license and attribution plan first.

Keep credentials, tokens, raw API responses, device IDs, account IDs, MAC
addresses, and home-specific data out of the repo. Use redacted fixtures for
tests.

Prefer the standard Home Assistant shape: `custom_components/perific`, config
flow, async API client, `DataUpdateCoordinator`, device/entity registry
metadata, diagnostics, translations, and focused tests.

Use `.python-version` for the default development interpreter and
`pyproject.toml` for the supported Python range. Use `uv run ruff format
--check .` and `uv run ruff check .` for Python formatting and linting. Ruff
uses `select = ["ALL"]` with explicit ignores for formatter conflicts and
non-correctness documentation policy. Ruff checks intentionally exclude
`.agents/`.

Use `uv run pre-commit install` to enable local Git hooks. The hooks must call
repo-owned `uv run` checks instead of separate global linter installations.

Expose observable meter facts with explicit units. Grid power for energy
management must be watts unless a consuming interface documents another unit.

Stop and ask for input when live credentials, private API data, device identity,
Home Assistant installation access, or external endorsement is required.

Do not call the integration official, certified, or supported by Perific/Enegic
unless that endorsement is documented by the vendor.

Before committing, run `uv run pre-commit run --all-files` plus any focused
tests that prove the touched contract, then scan staged changes for secrets.
