#!/bin/bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
OUT="$ROOT/dist"
APP="$OUT/Orcha.app"
RES="$APP/Contents/Resources/orcha"
MACOS="$APP/Contents/MacOS"
DMGROOT="$OUT/dmg-root"
rm -rf "$OUT"
mkdir -p "$RES" "$MACOS" "$DMGROOT"
for item in app mcp_servers studio config skills knowledge docs scripts tests Modelfile.v3 Modelfile.v3.max Modelfile.v3.quality Modelfile.logic-0.8b README.md LICENSE LICENSE-NOTE.md CHANGELOG.md .orchaignore; do
  [ -e "$ROOT/$item" ] && cp -R "$ROOT/$item" "$RES/"
done
cat > "$MACOS/Orcha" <<'LAUNCH'
#!/bin/bash
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../Resources/orcha" && pwd)"
PORT="${ORCHA_PORT:-11435}"
URL="http://127.0.0.1:${PORT}/"
export ORCHA_DATA_DIR="${ORCHA_DATA_DIR:-$HOME/Library/Application Support/Orcha}"
export ORCHA_DATA_DIR="${ORCHA_DATA_DIR:-$ORCHA_DATA_DIR}"
mkdir -p "$ORCHA_DATA_DIR" "$HOME/Library/Logs"
if ! command -v python3 >/dev/null 2>&1; then osascript -e 'display alert "Orcha" message "Chưa có Python 3. Hãy cài Python 3.10+ trước." as critical' || true; open "https://www.python.org/downloads/macos/" || true; exit 1; fi
if ! curl -fsS "http://127.0.0.1:11434/api/tags" >/dev/null 2>&1 && [ -d "/Applications/Ollama.app" ]; then open -gja "Ollama" || true; sleep 1; fi
if ! python3 "$ROOT/scripts/desktop_control.py" health --port "$PORT"; then
  python3 "$ROOT/scripts/desktop_control.py" stop --port "$PORT" || true
  sleep 0.5
  nohup python3 "$ROOT/app/studio_server_v77.py" --host 127.0.0.1 --port "$PORT" --profile balanced >"$HOME/Library/Logs/Orcha.log" 2>&1 &
fi
ready=false
for _ in $(seq 1 60); do
  if python3 "$ROOT/scripts/desktop_control.py" health --port "$PORT"; then ready=true; break; fi
  sleep 0.25
done
if [ "$ready" != true ]; then osascript -e 'display alert "Orcha" message "Không khởi động được runtime v7.7." as critical' || true; exit 1; fi
if [ -d "/Applications/Google Chrome.app" ]; then open -na "Google Chrome" --args --app="$URL"; elif [ -d "/Applications/Microsoft Edge.app" ]; then open -na "Microsoft Edge" --args --app="$URL"; else open "$URL"; fi
LAUNCH
chmod +x "$MACOS/Orcha"
cat > "$APP/Contents/Info.plist" <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
<key>CFBundleName</key><string>Orcha</string>
<key>CFBundleDisplayName</key><string>Orcha</string>
<key>CFBundleIdentifier</key><string>app.orcha.desktop</string>
<key>CFBundleVersion</key><string>7.7.0</string>
<key>CFBundleShortVersionString</key><string>7.7.0</string>
<key>CFBundleExecutable</key><string>Orcha</string>
<key>LSMinimumSystemVersion</key><string>12.0</string>
<key>NSHighResolutionCapable</key><true/>
</dict></plist>
PLIST
cp -R "$APP" "$DMGROOT/"
ln -s /Applications "$DMGROOT/Applications"
hdiutil create -volname "Orcha" -srcfolder "$DMGROOT" -ov -format UDZO "$OUT/Orcha-v7-macOS.dmg"
