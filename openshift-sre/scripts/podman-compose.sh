#!/usr/bin/env bash
set -euo pipefail

if command -v podman-compose >/dev/null 2>&1; then
  exec podman-compose "$@"
fi

if command -v podman >/dev/null 2>&1; then
  exec podman compose "$@"
fi

echo "Podman is not installed or not on PATH." >&2
exit 1
