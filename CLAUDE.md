# edit-videos-poc

動画編集 PoC: 無音カット → 文字起こし → Gemini で字幕整形 → 焼き込みレンダリング。

## フェーズと方針

- **PoC（現在）**: Colab GPU ランタイムで動かす。処理本体は `src/edit_videos_poc/` のモジュール、notebook は薄いエントリ。
- **将来**: 常駐サーバー化（FastAPI 想定）。今のうちから「セッション固有状態を持たない関数」で書く。

## 開発ルール

### ffmpeg 実行
- `subprocess.run(..., capture_output=True, text=True)` を使う。失敗時は **stderr を例外メッセージに含める**
- 共通ヘルパー `pipeline._ffmpeg.run_ffmpeg` を経由する（重複させない）

### 長時間処理は自動実行しない
- 動画レンダリング・large-v3 文字起こしは数分〜数十分。**ユーザーに確認してから走らせる**
- 動作確認は 10 秒程度の切り出しサンプルで

### 字幕タイムコード
- **無音カットを先にやると Whisper のタイムコードがズレる**
- 推奨順序: ① 音声抽出 → ② 文字起こし（元動画の時間軸） → ③ 無音検出 → ④ SRT と動画を **同じカット情報で同期シフト** → ⑤ 焼き込み

### パス管理
- 中間ファイルは `config.step_dir(name)` で取得（`output/{step}/`）
- Colab は `/content/output/` を自動選択（`COLAB_RELEASE_TAG` 環境変数で判定）

### API キー
- `.env` から `python-dotenv` 経由で読む。**コミットしない**
- 新しいキーが増えたら `.env.example` を更新

### Whisper モデル
- デフォルト `large-v3`。Colab 無料枠が厳しければ `WHISPER_MODEL=medium` で env 上書き
- GPU で `float16`、CPU で `int8` を `transcribe._select_runtime()` が自動選択

### Gemini
- per-segment 呼び出しはコストがかかる。本番化時はバッチプロンプトに切り替え検討
- モデル名は `GEMINI_MODEL` env で上書き可能

### コーディング
- public 関数のみ 1 行 docstring。WHY が非自明なときだけインラインコメント
- `from __future__ import annotations` を全モジュール先頭に
- 重い import（torch / faster_whisper / google.generativeai）は **関数内で lazy import**

### 依存管理
- `uv pip install -e .` でローカル開発、Colab では `!pip install -e .`
- 新規依存は `pyproject.toml` の `dependencies` に追記
