# edit-videos-poc

動画の無音カット・文字起こし・字幕焼き込みを自動化する Python PoC です。  
**Web UI** または **GitHub Actions** から実行できます。

---

## 機能

| パイプライン | 説明 |
|---|---|
| **Video Pipeline** | 横動画に無音カット＋字幕を焼き込む |
| **Short Video Pipeline** | 縦型 9:16 ショート動画に変換（ぼかし/単色/静止画背景） |
| **Clip Video** | 指定秒数で切り抜き＋上下テキスト合成 |

---

## クイックスタート（Web UI）

```bash
# 依存インストール
uv sync

# サーバー起動
uv run python scripts/run_server.py

# ブラウザで http://localhost:8000 を開く
```

> **必要な環境変数**（`.env` に記載）
> ```
> GEMINI_API_KEY=your_key   # Video / Short パイプラインで必要
> OPENAI_API_KEY=your_key   # サムネイル生成（オプション）
> ```

### Web UI の使い方

1. 動画ファイル（MP4 / MOV / WAV）をドラッグ＆ドロップ
2. パイプライン（Video / Short / Clip）を選択して設定を入力
3. 「実行する」をクリック
4. ジョブ一覧で進捗を確認し、完了後に「↓ ダウンロード」

**ジョブ管理**
- 同時実行: 最大 5 件
- キュー: 最大 20 件
- 成果物の保存先: `output/jobs/{job_id}/`

---

## GitHub Actions から実行

リポジトリの **Actions** タブから `workflow_dispatch` で各ワークフローを手動実行できます。

### 必要な Secrets

| Secret 名 | 用途 |
|---|---|
| `GEMINI_API_KEY` | 字幕フィラー除去（Video / Short） |
| `OPENAI_API_KEY` | サムネイル生成（オプション） |

### ワークフロー一覧

#### Run Video Pipeline
通常の横動画を処理します。

| 入力 | デフォルト | 説明 |
|---|---|---|
| `video_path` | — | リポジトリ内の動画パス（例: `samples/input.mp4`） |
| `language` | `ja` | 文字起こし言語 |
| `whisper_model` | `medium` | `tiny` / `base` / `small` / `medium` / `large-v3` |
| `font_color` | `yellow` | 字幕色（`yellow` / `white` / `red` / `blue` など） |
| `noise_db` | `-30` | 無音判定閾値 (dB) |
| `min_silence` | `0.5` | 最小無音長 (秒) |
| `skip_refine` | `false` | Gemini フィラー除去をスキップ |
| `thumbnail` | `false` | gpt-image-2 でサムネイル生成 |

#### Run Short Video Pipeline
縦型 9:16 のショート動画を作成します。

| 入力 | デフォルト | 説明 |
|---|---|---|
| `video_path` | — | リポジトリ内の動画パス |
| `background_type` | `blur` | `blur`（動画ぼかし）/ `color`（単色）/ `image`（静止画ぼかし） |
| `background_color` | `black` | `color` 選択時の背景色 |
| `background_image` | — | `image` 選択時の静止画パス |
| `blur_sigma` | `40` | ぼかし強度 |
| `font_color` | `yellow` | 字幕色 |
| `language` | `ja` | 文字起こし言語 |
| `whisper_model` | `medium` | Whisper モデル |

#### Clip Video
指定した秒数で切り抜き、上下にテキストを合成します。

| 入力 | デフォルト | 説明 |
|---|---|---|
| `video_path` | — | リポジトリ内の動画パス |
| `start_time` | — | 切り抜き開始時間（秒 または `HH:MM:SS`） |
| `end_time` | — | 終了時間（省略で末尾まで） |
| `top_text` | — | 上部中央テキスト（省略可） |
| `bottom_text` | — | 下部中央テキスト（省略可） |
| `text_color` | `white` | テキスト色 |
| `font_size` | `108` | フォントサイズ |

---

## コマンドラインから実行

```bash
# Video Pipeline
uv run python scripts/run_pipeline.py samples/input.mp4 --language ja --font-color yellow

# Short Video Pipeline
uv run python scripts/run_short.py samples/input.mp4 --language ja

# Clip Video
uv run python scripts/run_clip.py samples/input.mp4 --start 10 --end 40 --top-text "タイトル"
```

---

## 処理フロー（Video / Short）

```
① 音声抽出 (ffmpeg)
② 文字起こし (faster-whisper)
③ 無音区間検出 (ffmpeg silencedetect)
④ フィラー除去 (Gemini API) ※ --skip-refine でスキップ可
⑤ ASS 字幕生成（二重縁取り対応）
⑥ 無音カット＋字幕焼き込み (ffmpeg)
⑦ 9:16 縦型変換 (ffmpeg) ※ Short のみ
```

---

## セットアップ

```bash
# リポジトリ取得
git clone https://github.com/lisso-hookah/edit-videos-poc.git
cd edit-videos-poc

# uv インストール（未インストールの場合）
curl -LsSf https://astral.sh/uv/install.sh | sh

# 依存インストール
uv sync

# 環境変数設定
cp .env.example .env
# .env を編集して API キーを設定
```

**システム依存**
```bash
# Ubuntu / Debian
sudo apt-get install ffmpeg fonts-noto-cjk fontconfig
```

---

## プロジェクト構成

```
edit-videos-poc/
├── scripts/
│   ├── run_pipeline.py   # Video Pipeline エントリ
│   ├── run_short.py      # Short Video Pipeline エントリ
│   ├── run_clip.py       # Clip Video エントリ
│   └── run_server.py     # Web サーバー起動
├── src/edit_videos_poc/
│   ├── pipeline/
│   │   ├── audio.py      # 音声抽出
│   │   ├── transcribe.py # Whisper 文字起こし
│   │   ├── silence.py    # 無音検出
│   │   ├── refine.py     # Gemini フィラー除去
│   │   ├── srt_utils.py  # ASS 字幕生成
│   │   ├── render.py     # ffmpeg レンダリング
│   │   ├── vertical.py   # 9:16 縦型変換
│   │   ├── clip.py       # 切り抜き＋テキスト合成
│   │   └── thumbnail.py  # gpt-image-2 サムネイル生成
│   └── web/
│       ├── app.py        # FastAPI アプリ
│       ├── queue_manager.py  # ジョブキュー
│       ├── jobs.py       # ジョブ実行
│       └── static/
│           └── index.html    # フロントエンド
├── .github/workflows/
│   ├── run-pipeline.yml
│   ├── run-short.yml
│   └── run-clip.yml
└── output/               # 成果物出力先
```
