# Perific/Enegic API Verification

This repository keeps a clean-room API contract in
[`api/perific.openapi.yaml`](../api/perific.openapi.yaml). The contract starts
with independently observed route and method facts only. Request and response
schemas stay broad until they are proven from vendor documentation or
user-approved, redacted live traffic.

## Authority

- Vendor documentation or support confirmation, when available.
- Public, unauthenticated probes against `https://api.enegic.com` for route and
  method existence only.
- User-approved credentialed traffic captured locally and redacted before it is
  committed as a fixture or summarized in docs.
- Community projects may supply candidate endpoints to check, but they are not
  authority and their specs, clients, models, mappings, fixtures, and prose must
  not be copied into this repository.

## Schema Maintenance

Treat [`api/perific.openapi.yaml`](../api/perific.openapi.yaml) as the current
verified contract, not a fixed upstream spec. When live schema-only evidence
shows a better endpoint, field, type, or parser boundary, update the spec, code,
and tests to match that evidence. Record only redacted field names, types, and
behavior; keep raw responses out of git.

## Current Public Observations

Observed on 2026-06-22 against `https://api.enegic.com`.

| Endpoint | Observation | Contract status |
| --- | --- | --- |
| `/` | `GET` returns `404` with a Nancy page. | No public API index found. |
| `/.well-known/openid-configuration` | `GET` returns `404`. | No public OIDC discovery found. |
| `/.well-known/oauth-authorization-server` | `GET` returns `404`. | No public OAuth authorization-server metadata found. |
| `/createtoken` | `OPTIONS` allows `PUT`; `GET` returns `405`. | Route and method only. Schema pending. |
| `/getaccountoverview` | `OPTIONS` allows `GET, PUT`; `GET` returns `401`. | Route, method, and auth requirement only. Schema pending. |
| `/getlatestpackets` | `OPTIONS` allows `PUT`; `GET` returns `405`. | Route and method only. Schema pending. |
| `/getreporterssettingsforuser` | `OPTIONS` allows `GET`; `GET` returns `401`. | Metadata candidate only. Schema pending. |

The local Python TLS trust path may fail on enterprise TLS inspection chains.
Treat that as a local discovery environment issue: disconnect the VPN, repair
the local trust path, or use a verification-preserving local probe workaround.
Runtime code must keep normal TLS certificate verification enabled.

Repeat public route/method checks with:

```sh
scripts/probe-public-api.sh
```

The script records HTTP status and `Allow` headers only. It does not send
credentials, request bodies, tokens, or private identifiers.

Keep this probe out of pre-commit and default automated tests; run it only as
an explicit live check.

## Credentialed Observations

Observed on 2026-06-22 with user-approved local credentials. No tokens,
credentials, private identifiers, raw payloads, or meter values were committed.

| Endpoint | Observation | Contract status |
| --- | --- | --- |
| `/createtoken` | `PUT` with username and password returns a token object with token creation and validity fields. | Native token auth verified. |
| `/getaccountoverview` | `GET` and `PUT {}` with `X-Authorization` return `200`; an invalid token returns `401`. | Token header verified. Schema still broad. |
| `/getlatestpackets` | `PUT {}` with `X-Authorization` returns latest packet data; an invalid token returns `401`. | First telemetry schema verified for selected fields. |

`PhaseMinute.data.hwi` and `PhaseMinute.data.hwo` are cumulative import/export
energy counters with an observed kilowatt-hour scale. Do not publish `hwi -
hwo` as instantaneous watts. Derive net grid power from consecutive
`PhaseMinute` samples with increasing timestamps:
`((delta_hwi_kwh - delta_hwo_kwh) * 1000 * 3600000) / delta_ms`.

Reject stale `PhaseMinute.ts` values instead of publishing unbounded stale
power. The runtime currently treats `PhaseMinute` packets older than 5 minutes
as stale, exposes the rejected packet timestamp when available, and resets the
delta baseline after overlong sample gaps. Counter decreases start a new
candidate baseline and require another monotonic sample before publishing
power.
`PhaseRealTime.data.hiavg[]` and `huavg[]` provide current and voltage
telemetry, but they do not provide net import/export direction and are not the
primary grid-power source.

## First Slice Boundary

The first implementation slice owns:

- the clean-room OpenAPI scaffold;
- the public route/method verification record;
- explicit pending fields for request bodies, response bodies, auth behavior,
  identifiers, units, and staleness semantics.

It now also owns the first Home Assistant config-flow implementation, native
token exchange, reauth path, and one read-only grid power sensor.

It does not own:

- control, pricing, history, or load-balancing endpoints;
- copied community schemas or generated code.

## Credentialed Verification Gate

Before runtime auth or telemetry parsing is implemented, verify the minimum
read-only path locally with user-approved credentials:

1. Confirm whether vendor OAuth/OIDC exists through official docs, browser
   traffic, or authenticated API traffic.
2. If OAuth/OIDC is still absent, obtain explicit approval before using native
   Perific token auth.
3. Capture only the minimum responses needed for:
   `/createtoken`, `/getaccountoverview`, and `/getlatestpackets`.
4. Redact tokens, emails, account IDs, device IDs, reporter IDs, serials, MAC
   addresses, addresses, and home-specific values before committing fixtures.
5. Update the OpenAPI schemas only for fields proven by the redacted evidence.
6. Create focused tests from the redacted fixtures before adding Home Assistant
   entities.

Credentials and raw API responses must stay out of git and out of chat.

## Code Generation Position

OpenAPI Generator currently documents Python client templates with `library`
options including `asyncio` and `httpx`. Async generation is therefore possible,
but code generation is not the first gate for this integration. The first gate
is verified payload shape and Home Assistant fit.

Generated code may be introduced later only if:

- it is generated from this repository's verified spec;
- the generator and templates produce async code that fits Home Assistant's
  shared-session and error-handling patterns;
- the generated output is reproducible and reviewable;
- generated files do not obscure the small runtime surface needed by the
  integration.
