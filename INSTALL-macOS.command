#!/bin/bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
echo "KimiK3-Lite Studio v5 - macOS setup"
if ! command -v python3 >/dev/null 2>&1; then
  echo "[MISSING] Python 3.10+"; open "https://www.python.org/downloads/macos/" || true
else
  echo "[OK] $(python3 --version)"
fi
if command -v ollama >/dev/null 2>&1 || [ -x "/Applications/Ollama.app/Contents/Resources/ollama" ]; then
  echo "[OK] Ollama"
else
  echo "[MISSING] Ollama"; open "https://ollama.com/download/mac" || true
fi
mkdir -p "$HOME/Library/Application Support/KimiK3-Lite Studio"
chmod +x "$ROOT/KimiK3 Studio.command" "$ROOT/Stop KimiK3 Studio.command" 2>/dev/null || true
read -r -p "Setup check completed. Press Enter to close..." _
