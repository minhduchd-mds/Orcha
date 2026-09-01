#!/bin/bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
PORT="${KIMIK3_PORT:-11435}"
URL="http://127.0.0.1:${PORT}/"
export KIMIK3_DATA_DIR="${KIMIK3_DATA_DIR:-$HOME/Library/Application Support/KimiK3-Lite Studio}"
mkdir -p "$KIMIK3_DATA_DIR" "$HOME/Library/Logs"
if ! command -v python3 >/dev/null 2>&1; then
  osascript -e 'display alert "KimiK3-Lite Studio" message "Chưa có Python 3. Hãy cài Python 3.10+ rồi mở lại ứng dụng." as critical' >/dev/null 2>&1 || true
  open "https://www.python.org/downloads/macos/" || true
  exit 1
fi
if ! curl -fsS "http://127.0.0.1:11434/api/tags" >/dev/null 2>&1 && [ -d "/Applications/Ollama.app" ]; then
  open -gja "Ollama" || true
  sleep 1
fi
if ! curl -fsS "${URL}health" >/dev/null 2>&1; then
  nohup python3 "$ROOT/app/studio_server_v66.py" --host 127.0.0.1 --port "$PORT" --profile balanced >"$HOME/Library/Logs/KimiK3-Lite-Studio.log" 2>&1 &
fi
for _ in $(seq 1 40); do curl -fsS "${URL}health" >/dev/null 2>&1 && break; sleep 0.25; done
if [ -d "/Applications/Google Chrome.app" ]; then
  open -na "Google Chrome" --args --app="$URL"
elif [ -d "/Applications/Microsoft Edge.app" ]; then
  open -na "Microsoft Edge" --args --app="$URL"
else
  open "$URL"
fi
