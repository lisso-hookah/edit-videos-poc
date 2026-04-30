# edit-videos-poc

動画の無音カット・文字起こし・字幕焼き込みを自動化する Python プロジェクトです。

---

## アーキテクチャ

```
ブラウザ
  │  HTTPS
  ▼
Lollipop サーバー
  ├─ index.html    フロントエンド（SPA）
  ├─ api.php       ジョブキュー + ファイル保管（7日）
  └─ data/
       ├─ uploads/   アップロード動画（処理前）
       └─ results/   処理済み動画（ダウンロード用）
          │
          │ HTTPS ポーリング（5秒ごと）
          ▼
Windows 11 ローカル PC
  └─ run_worker.py  動画処理エンジン
       ├─ faster-whisper（文字起こし）
       ├─ Gemini API（フィラー除去）
       └─ ffmpeg（カット・字幕焼き込み・縦型変換）
```

- **ローカル PC → Lollipop の HTTPS アウトバウンドのみ**。ポート開放・SSH トンネル不要
- Lollipop はジョブ管理とファイル保管のみ。処理はすべてローカルで実行
- アップロード動画・処理済み動画は **7日後に自動削除**

---

## 機能

| パイプライン | 説明 |
|---|---|
| **Video Pipeline** | 横動画に無音カット＋字幕を焼き込む |
| **Short Video Pipeline** | 縦型 9:16 ショート動画に変換（ぼかし／単色／静止画背景） |
| **Clip Video** | 指定秒数で切り抜き＋上下テキスト合成 |

---

## セットアップ

### 必要なもの

| ツール | 用途 |
|---|---|
| Python 3.11+ | ローカル Worker |
| [uv](https://docs.astral.sh/uv/) | Python パッケージ管理 |
| ffmpeg | 動画処理（PATH に追加） |
| ロリポップ スタンダード以上 | フロントエンド＋ファイル保管 |
| Gemini API キー | 字幕フィラー除去（Video / Short） |
| OpenAI API キー | サムネイル生成（任意） |

---

### 1. ロリポップ側のセットアップ

#### 1-1. ファイルをアップロード

ロリポップのファイルマネージャーまたは FTP で、対象ドメインの**公開ディレクトリ**（例: `public_html/`）に以下をアップロードします。

```
deploy/lollipop/
├── api.php        → 公開ディレクトリ直下
├── index.html     → 公開ディレクトリ直下
├── .htaccess      → 公開ディレクトリ直下
└── data/
    └── .htaccess  → data/ フォルダを作成して中に配置
```

#### 1-2. WORKER_KEY を設定

`api.php` の先頭にある `WORKER_KEY` をランダムな文字列に変更します（ローカル Worker と必ず一致させる）。

```php
define('WORKER_KEY', 'ここを長いランダム文字列に変更');
```

> **生成例**: パスワードマネージャーや `openssl rand -hex 32` コマンドで生成

---

### 2. ローカル PC（Windows 11）のセットアップ

#### 2-1. リポジトリを取得

```powershell
git clone https://github.com/lisso-hookah/edit-videos-poc.git
cd edit-videos-poc
```

#### 2-2. uv をインストール（未導入の場合）

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

#### 2-3. 依存パッケージをインストール

```powershell
uv sync
```

#### 2-4. ffmpeg をインストール

[ffmpeg.org](https://ffmpeg.org/download.html) からダウンロードして PATH に追加します。

確認:
```powershell
ffmpeg -version
```

#### 2-5. 環境変数を設定

`.env.example` をコピーして `.env` を作成し、各値を設定します。

```powershell
copy .env.example .env
```

```env
# Gemini API キー（Video / Short パイプラインで必要）
GEMINI_API_KEY=your_gemini_key

# OpenAI API キー（サムネイル生成、任意）
OPENAI_API_KEY=your_openai_key

# ロリポップのドメイン（末尾スラッシュなし）
LOLLIPOP_API_URL=https://your-domain.example.com

# api.php の WORKER_KEY と同じ値
WORKER_KEY=ここを長いランダム文字列に変更
```

#### 2-6. Worker を起動

```powershell
uv run python scripts\run_worker.py
```

起動すると 5 秒ごとにロリポップへポーリングします。ジョブが投入されると自動的に処理を開始します。

```
[worker] 起動 → https://your-domain.example.com
[worker] Ctrl+C で停止
```

---

### 3. 使い方

1. ブラウザで `https://your-domain.example.com` を開く
2. 動画ファイル（MP4 / MOV / WAV）をドラッグ＆ドロップ
3. パイプライン（Video / Short / Clip）を選択して設定を入力
4. 「実行する」をクリック
5. ジョブ一覧でリアルタイムの進捗を確認
6. 完了後、「↓ ダウンロード」から処理済み動画を取得

> Worker（ローカル PC）が起動していない場合、ジョブは「待機中」のままになります

---

## パイプライン設定

### Video Pipeline（横動画・字幕付き）

| 設定項目 | デフォルト | 説明 |
|---|---|---|
| 言語 | `ja` | 文字起こし言語 |
| Whisper モデル | `medium` | `tiny` / `base` / `small` / `medium` / `large-v3` |
| 字幕カラー | `yellow` | `yellow` / `white` / `red` / `blue` / `green` / `orange` / `black` |
| 無音閾値 (dB) | `-30` | 小さいほど無音を検出しにくい |
| 最小無音長 (秒) | `0.5` | これより短い無音はカットしない |
| Gemini 除去スキップ | `false` | フィラー除去を省略（高速化） |
| サムネイル生成 | `false` | gpt-image-2 で概要画像を生成（OpenAI 必要） |

### Short Video Pipeline（縦型 9:16）

| 設定項目 | デフォルト | 説明 |
|---|---|---|
| 背景タイプ | `blur` | `blur`（動画ぼかし）/ `color`（単色）/ `image`（静止画ぼかし） |
| 背景色 | `black` | `color` 選択時に有効 |
| 背景画像 | — | `image` 選択時にアップロード |
| ぼかし強度 | `40` | `blur` / `image` 選択時に有効 |

### Clip Video（切り抜き）

| 設定項目 | デフォルト | 説明 |
|---|---|---|
| 開始時間 | 必須 | 秒数 または `HH:MM:SS` |
| 終了時間 | — | 省略で末尾まで |
| 上部テキスト | — | 画面中央より上に表示 |
| 下部テキスト | — | 画面中央より下に表示 |
| テキストカラー | `white` | `white` / `yellow` / `red` / `orange` / `black` |
| フォントサイズ | `108` | drawtext フォントサイズ |

---

## 処理フロー（Video / Short）

```
① 音声抽出          ffmpeg
② 文字起こし        faster-whisper
③ 無音区間検出      ffmpeg silencedetect
④ フィラー除去      Gemini API（--skip-refine でスキップ可）
⑤ ASS 字幕生成     二重縁取り対応
⑥ 無音カット＋字幕焼き込み  ffmpeg
⑦ 9:16 縦型変換    ffmpeg（Short のみ）
```

---

## コマンドラインから実行（ローカル単体）

Worker を経由せず、直接スクリプトを実行することもできます。

```powershell
# Video Pipeline
uv run python scripts\run_pipeline.py videos\input.mp4 --language ja --font-color yellow

# Short Video Pipeline
uv run python scripts\run_short.py videos\input.mp4 --language ja

# Clip Video
uv run python scripts\run_clip.py videos\input.mp4 --start 10 --end 40 --top-text "タイトル"
```

---

## GitHub Actions から実行

ロリポップ Worker が使えない環境での代替手段として、GitHub Actions でも処理を実行できます。

**Actions → 各ワークフロー → Run workflow** から手動実行し、成果物を Artifacts からダウンロードします。

| ワークフロー | 用途 |
|---|---|
| Run Video Pipeline | 横動画の字幕付き編集 |
| Run Short Video Pipeline | 縦型ショート動画作成 |
| Clip Video | 切り抜き＋テキスト合成 |

必要な Secrets: `GEMINI_API_KEY`（必須）、`OPENAI_API_KEY`（サムネイル生成時のみ）

---

## プロジェクト構成

```
edit-videos-poc/
├── deploy/lollipop/          ← ロリポップにアップロードするファイル
│   ├── api.php               REST API（ジョブ管理・ファイル保管・7日自動削除）
│   ├── index.html            SPA フロントエンド
│   ├── .htaccess             Apache ルーティング設定
│   └── data/
│       └── .htaccess         data/ への直接アクセスを拒否
│
├── scripts/
│   ├── run_worker.py         Windows ローカル Worker（常駐プロセス）
│   ├── run_pipeline.py       Video Pipeline CLI
│   ├── run_short.py          Short Video Pipeline CLI
│   ├── run_clip.py           Clip Video CLI
│   └── run_server.py         ローカル FastAPI サーバー（単体利用時）
│
├── src/edit_videos_poc/
│   ├── pipeline/
│   │   ├── audio.py          音声抽出
│   │   ├── transcribe.py     faster-whisper 文字起こし
│   │   ├── silence.py        無音検出
│   │   ├── refine.py         Gemini フィラー除去
│   │   ├── srt_utils.py      ASS 字幕生成（二重縁取り対応）
│   │   ├── render.py         ffmpeg レンダリング
│   │   ├── vertical.py       9:16 縦型変換
│   │   ├── clip.py           切り抜き＋テキスト合成
│   │   └── thumbnail.py      gpt-image-2 サムネイル生成
│   └── web/                  ローカル FastAPI サーバー（単体利用時）
│       ├── app.py
│       ├── queue_manager.py
│       ├── jobs.py
│       └── static/index.html
│
├── .github/workflows/
│   ├── run-pipeline.yml
│   ├── run-short.yml
│   └── run-clip.yml
│
├── .env.example              環境変数テンプレート
├── pyproject.toml
└── output/                   処理結果の出力先（ローカル実行時）
```

---

## ファイル保管とコスト

| ファイル種別 | 保管場所 | 保持期間 |
|---|---|---|
| アップロード動画（処理前） | Lollipop `data/uploads/` | 7日で自動削除 |
| 処理済み動画 | Lollipop `data/results/` | 7日で自動削除 |
| ジョブ状態 JSON | Lollipop `data/jobs/` | 7日で自動削除 |

- 自動削除はリクエストのたびに確率的に実行（約 5% の確率）
- Lollipop の使用可能ストレージの範囲内で運用
