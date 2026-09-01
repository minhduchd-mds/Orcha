#!/bin/bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
PORT="${KIMIK3_PORT:-11435}"
URL="http://127.0.0.1:${PORT}/"
export KIMIK3_DATA_DIR="${KIMIK3_DATA_DIR:-$HOME/Library/Application Support/KimiK3-Lite Studio}"
mkdir -p "$KIMIK3_DATA_DIR" "$HOME/Library/Logs"
if ! command -v python3 >/dev/null 2>&1; then osascript -e 'display alert "KimiK3-Lite Studio" message "Chưa có Python 3. Hãy cài Python 3.10+ rồi mở lại ứng dụng." as critical' >/dev/null 2>&1 || true; open "https://www.python.org/downloads/macos/" || true; exit 1; fi
if ! curl -fsS "http://127.0.0.1:11434/api/tags" >/dev/null 2>&1 && [ -d "/Applications/Ollama.app" ]; then open -gja "Ollama" || true; sleep 1; fi
health="$(curl -fsS "${URL}health" 2>/dev/null || true)"
if [[ "$health" != *'"version": "7.0.0"'* && "$health" != *'"version":"7.0.0"'* ]]; then
  curl -fsS -X POST -H 'Content-Type: application/json' -d '{}' "${URL}api/app/shutdown" >/dev/null 2>&1 || true
  sleep 0.5
  nohup python3 "$ROOT/app/studio_server_v70.py" --host 127.0.0.1 --port "$PORT" --profile balanced >"$HOME/Library/Logs/KimiK3-Lite-Studio.log" 2>&1 &
fi
for _ in $(seq 1 60); do
  health="$(curl -fsS "${URL}health" 2>/dev/null || true)"
  [[ "$health" == *'7.0.0'* && "$health" == *'deepseek_harness_patterns'* ]] && break
  sleep 0.25
done
if [[ "$health" != *'7.0.0'* ]]; then osascript -e 'display alert "KimiK3-Lite Studio" message "Không khởi động được runtime v7.0. Kiểm tra Python/Ollama và log trong ~/Library/Logs." as critical' >/dev/null 2>&1 || true; exit 1; fi
if [ -d "/Applications/Google Chrome.app" ]; then open -na "Google Chrome" --args --app="$URL"; elif [ -d "/Applications/Microsoft Edge.app" ]; then open -na "Microsoft Edge" --args --app="$URL"; else open "$URL"; fi
