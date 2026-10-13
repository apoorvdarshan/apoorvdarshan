#!/usr/bin/env bash
set -euo pipefail
if command -v tectonic >/dev/null; then exit 0; fi
archive="$(mktemp)"
trap 'rm -f "$archive"' EXIT
curl --fail --silent --show-error --location --retry 3 \
  'https://github.com/tectonic-typesetting/tectonic/releases/download/tectonic%400.17.0/tectonic-0.17.0-x86_64-unknown-linux-gnu.tar.gz' -o "$archive"
printf '%s  %s\n' '1a715688baf591e650c8aeb160ae934e181685eecbb38b317de30b269ac5d606' "$archive" | sha256sum --check
mkdir -p "$HOME/.local/bin"
tar -xzf "$archive" -C "$HOME/.local/bin" tectonic
echo "$HOME/.local/bin" >> "$GITHUB_PATH"
