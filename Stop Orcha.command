#!/bin/bash
set -euo pipefail
PORT="${ORCHA_PORT:-11435}"
curl -fsS -X POST -H 'Content-Type: application/json' -d '{}' "http://127.0.0.1:${PORT}/api/app/shutdown" >/dev/null 2>&1 || true
pkill -f "app/studio_server_v70.py.*--port ${PORT}" >/dev/null 2>&1 || true
osascript -e 'display notification "Orcha đã dừng" with title "Orcha"' >/dev/null 2>&1 || true
