#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="$SCRIPT_DIR/.venv/bin/python"
LOG_DIR="$SCRIPT_DIR/logs"

if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "Virtual environment tapilmadi: $PYTHON_BIN" >&2
  exit 1
fi

mkdir -p "$LOG_DIR"

STAMP="$(date '+%Y-%m-%d_%H-%M-%S')"
LOG_FILE="$LOG_DIR/news-agent-$STAMP.log"

echo "[$(date '+%F %T')] News agent started" | tee -a "$LOG_FILE"
"$PYTHON_BIN" "$SCRIPT_DIR/run.py" >> "$LOG_FILE" 2>&1
EXIT_CODE=$?
echo "[$(date '+%F %T')] News agent finished with code $EXIT_CODE" | tee -a "$LOG_FILE"

exit "$EXIT_CODE"
