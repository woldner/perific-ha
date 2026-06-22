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

The local Python TLS trust path failed certificate verification for the public
probe with `Basic Constraints of CA cert not marked critical`. The observations
above were collected without credentials and with certificate verification
disabled for the manual probe only. Runtime code must not disable TLS
verification.

Repeat public route/method checks with:

```sh
scripts/probe-public-api.sh
```

The script records HTTP status and `Allow` headers only. It does not send
credentials, request bodies, tokens, or private identifiers.

Keep this probe out of pre-commit and default automated tests; run it only as
an explicit live check.

## First Slice Boundary

The first implementation slice owns:

- the clean-room OpenAPI scaffold;
- the public route/method verification record;
- explicit pending fields for request bodies, response bodies, auth behavior,
  identifiers, units, and staleness semantics.

It does not own:

- Home Assistant config flows;
- native Perific token login;
- generated clients;
- sensor entities;
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
