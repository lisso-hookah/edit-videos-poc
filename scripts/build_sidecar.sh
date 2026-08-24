#!/usr/bin/env bash
# Build the Python FastAPI server into a single executable (sidecar for Tauri).
#
# Requirements:
#   pip install pyinstaller
#   pip install -e .
#
# Output: src-tauri/binaries/edit-videos-server-<triple>
#
set -e
cd "$(dirname "$0")/.."

TRIPLE=$(rustc -vV | awk '/host:/{print $2}')
OUT_DIR="src-tauri/binaries"
mkdir -p "$OUT_DIR"

echo "[sidecar] Building for $TRIPLE ..."

pyinstaller \
  --onefile \
  --name "edit-videos-server" \
  --hidden-import uvicorn.logging \
  --hidden-import uvicorn.loops \
  --hidden-import uvicorn.loops.auto \
  --hidden-import uvicorn.protocols \
  --hidden-import uvicorn.protocols.http \
  --hidden-import uvicorn.protocols.http.auto \
  --hidden-import uvicorn.protocols.websockets \
  --hidden-import uvicorn.protocols.websockets.auto \
  --hidden-import uvicorn.lifespan \
  --hidden-import uvicorn.lifespan.on \
  --hidden-import edit_videos_poc \
  --hidden-import edit_videos_poc.web \
  --hidden-import edit_videos_poc.web.app \
  --hidden-import edit_videos_poc.web.jobs \
  --hidden-import edit_videos_poc.web.queue_manager \
  scripts/server_entry.py

# Tauri expects the binary name to include the platform triple
cp "dist/edit-videos-server" "$OUT_DIR/edit-videos-server-${TRIPLE}"
echo "[sidecar] Done → $OUT_DIR/edit-videos-server-${TRIPLE}"
