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

The repository currently contains setup scaffolding only. Installation
instructions will be added after the first working integration version exists.
