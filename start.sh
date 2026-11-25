#!/usr/bin/env sh
# Edit Videos — ローカル起動（macOS / Linux）。uv が無ければ導入してから起動する。
set -e
cd "$(dirname "$0")"

if ! command -v uv >/dev/null 2>&1; then
  echo "[edit-videos] uv が見つかりません。https://astral.sh/uv からインストールします..."
  curl -LsSf https://astral.sh/uv/install.sh | sh
  PATH="$HOME/.local/bin:$PATH"
fi

echo "[edit-videos] 起動中...（初回は Python と依存パッケージの取得に数分かかります）"
exec uv run --frozen edit-videos "$@"
