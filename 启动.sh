#!/usr/bin/env bash
# HOI4 Mod Editor launcher (Linux/WSL)
# This is a thin wrapper. All path/env logic lives in launcher.py.
set -euo pipefail

SCRIPT_SOURCE="${BASH_SOURCE[0]}"
while [ -L "$SCRIPT_SOURCE" ]; do
  SCRIPT_DIR="$(cd -P "$(dirname -- "$SCRIPT_SOURCE")" && pwd)"
  SCRIPT_SOURCE="$(readlink -- "$SCRIPT_SOURCE")"
  case "$SCRIPT_SOURCE" in
    /*) ;;
    *) SCRIPT_SOURCE="$SCRIPT_DIR/$SCRIPT_SOURCE" ;;
  esac
done
SCRIPT_DIR="$(cd -P "$(dirname -- "$SCRIPT_SOURCE")" && pwd)"
cd "$SCRIPT_DIR"

if command -v python3 >/dev/null 2>&1 && \
   python3 -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)' >/dev/null 2>&1; then
  exec python3 -X utf8 "$SCRIPT_DIR/launcher.py" "$@"
fi

if command -v python >/dev/null 2>&1 && \
   python -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)' >/dev/null 2>&1; then
  exec python -X utf8 "$SCRIPT_DIR/launcher.py" "$@"
fi

echo "[ERROR] Python 3.10+ not found. Please install Python first." >&2
exit 1
