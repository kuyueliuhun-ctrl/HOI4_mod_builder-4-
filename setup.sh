#!/usr/bin/env bash
# HOI4 Mod Editor first-time setup (Linux/WSL)
# Delegates to the shared cross-platform launcher so paths stay identical.
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
exec bash "$SCRIPT_DIR/启动.sh" --setup --verify "$@"
