#!/bin/bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
OUT="$ROOT/dist"
APP="$OUT/KimiK3 Lite Studio.app"
RES="$APP/Contents/Resources/kimik3"
MACOS="$APP/Contents/MacOS"
DMGROOT="$OUT/dmg-root"
rm -rf "$OUT"
mkdir -p "$RES" "$MACOS" "$DMGROOT"
for item in app mcp_servers studio config skills knowledge docs scripts Modelfile.v3 Modelfile.v3.max Modelfile.v3.quality README.md LICENSE-NOTE.md CHANGELOG.md .kimik3ignore; do
  [ -e "$ROOT/$item" ] && cp -R "$ROOT/$item" "$RES/"
done
cat > "$MACOS/KimiK3 Lite Studio" <<'LAUNCH'
#!/bin/bash
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../Resources/kimik3" && pwd)"
PORT="${KIMIK3_PORT:-11435}"
URL="http://127.0.0.1:${PORT}/"
export KIMIK3_DATA_DIR="${KIMIK3_DATA_DIR:-$HOME/Library/Application Support/KimiK3-Lite Studio}"
mkdir -p "$KIMIK3_DATA_DIR" "$HOME/Library/Logs"
if ! command -v python3 >/dev/null 2>&1; then osascript -e 'display alert "KimiK3-Lite Studio" message "Chưa có Python 3. Hãy cài Python 3.10+ trước." as critical' || true; open "https://www.python.org/downloads/macos/" || true; exit 1; fi
if ! curl -fsS "http://127.0.0.1:11434/api/tags" >/dev/null 2>&1 && [ -d "/Applications/Ollama.app" ]; then open -gja "Ollama" || true; sleep 1; fi
health="$(curl -fsS "${URL}health" 2>/dev/null || true)"
if [[ "$health" != *'7.3.0'* || "$health" != *'project_executor_supervisor'* ]]; then
  curl -fsS -X POST -H 'Content-Type: application/json' -d '{}' "${URL}api/app/shutdown" >/dev/null 2>&1 || true
  sleep 0.5
  nohup python3 "$ROOT/app/studio_server_v70.py" --host 127.0.0.1 --port "$PORT" --profile balanced >"$HOME/Library/Logs/KimiK3-Lite-Studio.log" 2>&1 &
fi
for _ in $(seq 1 60); do
  health="$(curl -fsS "${URL}health" 2>/dev/null || true)"
  [[ "$health" == *'7.3.0'* && "$health" == *'project_executor_supervisor'* ]] && break
  sleep 0.25
done
if [[ "$health" != *'7.3.0'* ]]; then osascript -e 'display alert "KimiK3-Lite Studio" message "Không khởi động được runtime v7.3." as critical' || true; exit 1; fi
if [ -d "/Applications/Google Chrome.app" ]; then open -na "Google Chrome" --args --app="$URL"; elif [ -d "/Applications/Microsoft Edge.app" ]; then open -na "Microsoft Edge" --args --app="$URL"; else open "$URL"; fi
LAUNCH
chmod +x "$MACOS/KimiK3 Lite Studio"
cat > "$APP/Contents/Info.plist" <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
<key>CFBundleName</key><string>KimiK3 Lite Studio</string>
<key>CFBundleDisplayName</key><string>KimiK3 Lite Studio</string>
<key>CFBundleIdentifier</key><string>local.kimik3.lite.studio</string>
<key>CFBundleVersion</key><string>7.3.0</string>
<key>CFBundleShortVersionString</key><string>7.3.0</string>
<key>CFBundleExecutable</key><string>KimiK3 Lite Studio</string>
<key>LSMinimumSystemVersion</key><string>12.0</string>
<key>NSHighResolutionCapable</key><true/>
</dict></plist>
PLIST
cp -R "$APP" "$DMGROOT/"
ln -s /Applications "$DMGROOT/Applications"
hdiutil create -volname "KimiK3 Lite Studio" -srcfolder "$DMGROOT" -ov -format UDZO "$OUT/KimiK3-Lite-v7-macOS.dmg"
