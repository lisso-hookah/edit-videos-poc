#!/usr/bin/env bash
# Build the Python FastAPI server + bundled ffmpeg into a single executable (Tauri sidecar).
#
# Requirements:
#   pip install pyinstaller
#   pip install -e .
#   ffmpeg must be on PATH (the binary is detected and bundled automatically)
#
# Output: src-tauri/binaries/edit-videos-server-<triple>
#
set -e
cd "$(dirname "$0")/.."

TRIPLE=$(rustc -vV | awk '/host:/{print $2}')
OUT_DIR="src-tauri/binaries"
mkdir -p "$OUT_DIR"

# Locate ffmpeg / ffprobe binaries
FFMPEG_BIN=$(which ffmpeg)
FFPROBE_BIN=$(which ffprobe 2>/dev/null || true)

if [ -z "$FFMPEG_BIN" ]; then
  echo "ERROR: ffmpeg not found on PATH. Install it first."
  exit 1
fi

echo "[sidecar] Building for $TRIPLE ..."
echo "[sidecar] Bundling ffmpeg: $FFMPEG_BIN"

# Build --add-binary args
ADD_BINARY="--add-binary ${FFMPEG_BIN}:bin"
if [ -n "$FFPROBE_BIN" ]; then
  ADD_BINARY="$ADD_BINARY --add-binary ${FFPROBE_BIN}:bin"
fi

# Windows: binary names have .exe suffix; PyInstaller handles this automatically.
# The runtime hook (ffmpeg_hook.py) adds bin/ to PATH when the bundle starts.

pyinstaller \
  --onefile \
  --name "edit-videos-server" \
  $ADD_BINARY \
  --runtime-hook scripts/ffmpeg_hook.py \
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
BINARY="dist/edit-videos-server"
if [ -f "dist/edit-videos-server.exe" ]; then
  BINARY="dist/edit-videos-server.exe"
  cp "$BINARY" "$OUT_DIR/edit-videos-server-${TRIPLE}.exe"
  echo "[sidecar] Done → $OUT_DIR/edit-videos-server-${TRIPLE}.exe"
else
  cp "$BINARY" "$OUT_DIR/edit-videos-server-${TRIPLE}"
  echo "[sidecar] Done → $OUT_DIR/edit-videos-server-${TRIPLE}"
fi
