#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUN_SCRIPT="$SCRIPT_DIR/run_news_agent.sh"
START_MARKER="# BEGIN NEWS_AGENT"
END_MARKER="# END NEWS_AGENT"

if [[ ! -f "$RUN_SCRIPT" ]]; then
  echo "Run script tapilmadi: $RUN_SCRIPT" >&2
  exit 1
fi

TMP_FILE="$(mktemp)"

{
  crontab -l 2>/dev/null | sed "/$START_MARKER/,/$END_MARKER/d"
  echo "$START_MARKER"
  echo "CRON_TZ=Asia/Baku"
  echo "0 8 * * * $RUN_SCRIPT"
  echo "0 16 * * * $RUN_SCRIPT"
  echo "$END_MARKER"
} > "$TMP_FILE"

crontab "$TMP_FILE"
rm -f "$TMP_FILE"

echo "Cron ugurla quruldu:"
echo "- Her gun 08:00 Asia/Baku"
echo "- Her gun 16:00 Asia/Baku"
