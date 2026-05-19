#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

npm run build:ui
python3 -m mkdocs build --strict
bash ./scripts/podman-compose.sh -f compose.yaml up -d --build --force-recreate
