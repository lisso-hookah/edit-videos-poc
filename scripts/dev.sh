#!/usr/bin/env bash
# Run the Edit Videos app in dev mode (no Tauri — just open in browser)
set -e
cd "$(dirname "$0")/.."

echo "[dev] Starting Edit Videos server on http://localhost:18374"
echo "[dev] Press Ctrl+C to stop."
python -m edit_videos_poc.web.app --port 18374 --reload
