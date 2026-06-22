#!/usr/bin/env bash
set -euo pipefail

api_host="${PERIFIC_API_HOST:-https://api.enegic.com}"

paths=(
  "/"
  "/.well-known/openid-configuration"
  "/.well-known/oauth-authorization-server"
  "/createtoken"
  "/getaccountoverview"
  "/getlatestpackets"
  "/getreporterssettingsforuser"
)

for path in "${paths[@]}"; do
  url="${api_host}${path}"
  options_headers="$(mktemp)"
  get_headers="$(mktemp)"
  trap 'rm -f "${options_headers}" "${get_headers}"' EXIT

  options_status="$(
    curl --silent --show-error --output /dev/null \
      --dump-header "${options_headers}" \
      --request OPTIONS \
      --write-out "%{http_code}" \
      "${url}"
  )"
  allow_header="$(
    awk 'tolower($0) ~ /^allow:/ { sub(/\r$/, ""); print substr($0, 8) }' \
      "${options_headers}" \
      | paste -sd "," -
  )"

  get_status="$(
    curl --silent --show-error --output /dev/null \
      --dump-header "${get_headers}" \
      --request GET \
      --write-out "%{http_code}" \
      "${url}"
  )"

  printf '%-45s OPTIONS=%s Allow=%-10s GET=%s\n' \
    "${path}" \
    "${options_status}" \
    "${allow_header:-"-"}" \
    "${get_status}"

  rm -f "${options_headers}" "${get_headers}"
  trap - EXIT
done
