#!/bin/bash
pkill -f "app/studio_server.py.*--port 11435" >/dev/null 2>&1 || true
osascript -e 'display notification "Studio local đã dừng" with title "KimiK3-Lite"' >/dev/null 2>&1 || true
