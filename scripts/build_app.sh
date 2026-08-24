#!/usr/bin/env bash
# Full desktop app build: sidecar → Tauri bundle (.exe / .dmg / .deb)
#
# Requirements:
#   - Rust toolchain (rustup)
#   - Node.js >= 18 + npm
#   - pip install pyinstaller
#   - npm install (first run)
#
set -e
cd "$(dirname "$0")/.."

echo "=== Step 1/2: Build Python sidecar ==="
bash scripts/build_sidecar.sh

echo ""
echo "=== Step 2/2: Build Tauri app ==="
npm install --silent
npm run build

echo ""
echo "=== Build complete ==="
echo "Installer is in: src-tauri/target/release/bundle/"
