#!/usr/bin/env bash
set -euo pipefail
TASK_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exec uv run --project "$TASK_ROOT" python "$TASK_ROOT/scripts/quality_gate.py" "$@"
