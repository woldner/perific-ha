# Agent Instructions

This repo builds a clean-room Home Assistant custom integration for
Perific/Enegic meters.

Use current Home Assistant developer docs, this repo's source, tests, fixtures,
and explicit user constraints as authority. Treat community Perific repos and
forum posts as context only.

Do not copy code, generated clients, OpenAPI specs, fixtures, entity mappings,
or prose from other Perific integrations unless the user explicitly approves the
license and attribution plan first.

Keep credentials, tokens, raw API responses, device IDs, account IDs, MAC
addresses, and home-specific data out of the repo. Use redacted fixtures for
tests.

Prefer the standard Home Assistant shape: `custom_components/perific`, config
flow, async API client, `DataUpdateCoordinator`, device/entity registry
metadata, diagnostics, translations, and focused tests.

Expose observable meter facts with explicit units. Grid power for energy
management must be watts unless a consuming interface documents another unit.

Stop and ask for input when live credentials, private API data, device identity,
Home Assistant installation access, or external endorsement is required.

Do not call the integration official, certified, or supported by Perific/Enegic
unless that endorsement is documented by the vendor.

Before committing, run the smallest checks that prove the touched contract and
scan staged changes for secrets.
