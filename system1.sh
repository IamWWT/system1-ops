#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
RUNTIME_PYTHON="${SYSTEM1_PYTHON:-}"
if [[ -z "$RUNTIME_PYTHON" ]]; then
  if [[ -x "$SCRIPT_DIR/.venv/bin/python" ]]; then RUNTIME_PYTHON="$SCRIPT_DIR/.venv/bin/python"
  elif [[ -x "$SCRIPT_DIR/../laya/.venv/bin/python" ]]; then RUNTIME_PYTHON="$SCRIPT_DIR/../laya/.venv/bin/python"
  else RUNTIME_PYTHON="python3"; fi
fi
exec "$RUNTIME_PYTHON" "$SCRIPT_DIR/scripts/launch.py" manage "$@"
