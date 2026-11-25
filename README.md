# edit-videos-poc

動画の無音カット・文字起こし・字幕焼き込みを自動化する Python プロジェクトです。

動かし方は 2 通りあります。

| 方法 | 向いている場面 |
|---|---|
| **[ローカルで動かす](#ローカルで動かす)** | 自分の PC だけで完結させたい（サーバー・GitHub Actions 不要） |
| **[Lollipop + GitHub Actions](#アーキテクチャlollipop--github-actions-版)** | ブラウザから誰でも使える Web サービスとして公開したい |

---

## ローカルで動かす

必要なのは [uv](https://docs.astral.sh/uv/) だけです。Python 本体・依存パッケージ・ffmpeg は uv が `uv.lock` のとおりに揃えます。

```bash
git clone https://github.com/lisso-hookah/edit-videos-poc.git
cd edit-videos-poc
uv run edit-videos          # → http://127.0.0.1:8000 がブラウザで開く
```

コマンドを打ちたくない場合は、フォルダ内のランチャーをダブルクリックしてください（uv が無ければ導入してから起動します）。

| OS | ランチャー |
|---|---|
| Windows | `start.bat` |
| macOS | `start.command` |
| Linux | `./start.sh` |

- 初回起動は Python と依存パッケージの取得に数分、初回ジョブは Whisper モデルの取得（medium: 約 1.5 GB）に時間がかかります
- 終了は起動したウィンドウで Ctrl+C（またはウィンドウを閉じる）
- うまく動かないときは `uv run edit-videos doctor` で ffmpeg / GPU / フォント / API キーの状態を確認できます

### API キー（任意）

`.env.example` を `.env` にコピーして設定します。**キーが無くても動きます**（その場合フィラー除去はスキップされ、文字起こしのままの字幕になります）。

| キー | 用途 |
|---|---|
| `GEMINI_API_KEY` | 字幕のフィラー除去 |
| `OPENAI_API_KEY` | サムネイル生成（任意） |

### GPU（NVIDIA）で高速化

既定は CPU（int8）で動きます。NVIDIA GPU を使う場合は CUDA ライブラリ入りの extra を追加します。

```bash
uv sync --extra gpu
uv run edit-videos doctor   # Whisper: device=cuda になっていれば有効
```

GPU での文字起こしに失敗した場合は自動で CPU にフォールバックします。強制したいときは `.env` に `WHISPER_DEVICE=cpu`（または `cuda`）を設定してください。

### コマンドラインから直接実行

```bash
uv run edit-videos pipeline videos/input.mp4 --language ja --font-color yellow   # 横動画 + 字幕
uv run edit-videos short    videos/input.mp4 --language ja                       # 縦型 9:16
uv run edit-videos clip     videos/input.mp4 --start 10 --end 40 --top-text "タイトル"
```

出力は `./output/`（`WORK_DIR` で変更可）の `rendered/` / `vertical/` / `clip/` に入ります。

### ローカル版の設定（環境変数 / `.env`）

| 変数 | 既定 | 説明 |
|---|---|---|
| `WHISPER_MODEL` | `large-v3`（Web UI は画面で選択、既定 `medium`） | 文字起こしモデル |
| `WHISPER_DEVICE` | 自動 | `cpu` / `cuda` を強制 |
| `SUBTITLE_FONT` | OS の日本語フォント（Windows: Yu Gothic、macOS: Hiragino Sans、Linux: Noto Sans CJK JP 等） | 字幕フォント |
| `FFMPEG_BINARY` | PATH 上の ffmpeg → 同梱 ffmpeg | 使用する ffmpeg |
| `EDIT_VIDEOS_HOME` | リポジトリ直下 | Web UI のデータ（`uploads/`・`output/jobs/`・`.env`）の置き場所 |
| `EDIT_VIDEOS_MAX_JOBS` | `1` | 同時に実行するジョブ数 |
| `EDIT_VIDEOS_RETENTION_DAYS` | `7` | アップロード・ジョブ出力を起動時に自動削除するまでの日数（`0` で削除しない） |

LAN 内の別端末から使う場合は `uv run edit-videos --host 0.0.0.0`（認証は無いので信頼できるネットワーク内のみ）。

Windows 用インストーラーを作る場合は [installer/BUILD.md](installer/BUILD.md) を参照してください。

---

## アーキテクチャ（Lollipop + GitHub Actions 版）

```
ブラウザ
  │  HTTPS
  ▼
Lollipop サーバー
  ├─ index.html    フロントエンド（SPA）
  ├─ api.php       ジョブキュー + ファイル保管（7日）
  └─ data/
       ├─ config.php  設定ファイル（HTTP 直接アクセス遮断）
       ├─ uploads/    アップロード動画（処理前）
       └─ results/    処理済み動画（ダウンロード用）
          │
          │ GitHub Actions API (workflow_dispatch)
          ▼
GitHub Actions
  └─ ubuntu-latest ランナー
       ├─ faster-whisper（文字起こし）
       ├─ Gemini API（フィラー除去）
       └─ ffmpeg（カット・字幕焼き込み・縦型変換）
          │
          │ HTTPS POST（結果アップロード）
          ▼
Lollipop サーバー（data/results/ に保存）
```

- **ローカル PC 不要** — すべての処理を GitHub Actions の無料枠で実行
- Lollipop はジョブ管理とファイル保管のみ。処理は GitHub Actions で実行
- アップロード動画・処理済み動画は **7日後に自動削除**
- ローカル Worker（Windows）も引き続きオプションとして利用可能（`GITHUB_TOKEN` を空にする）

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

| ツール／サービス | 用途 |
|---|---|
| ロリポップ スタンダード以上 | フロントエンド＋ファイル保管 |
| GitHub リポジトリ | Actions ランナー（無料枠） |
| Gemini API キー | 字幕フィラー除去（Video / Short） |
| OpenAI API キー | サムネイル生成（任意） |

---

### 1. GitHub Secrets の設定

リポジトリの **Settings → Secrets and variables → Actions** で以下を登録します。

| Secret 名 | 内容 |
|---|---|
| `GEMINI_API_KEY` | Gemini API キー（必須） |
| `LOLLIPOP_WORKER_KEY` | `config.php` の `WORKER_KEY` と同じ値（必須） |
| `OPENAI_API_KEY` | OpenAI API キー（サムネイル生成時のみ） |

---

### 2. GitHub PAT の取得

Lollipop PHP が GitHub Actions を起動するために Personal Access Token (PAT) が必要です。

1. [https://github.com/settings/tokens](https://github.com/settings/tokens) → **Generate new token (classic)**
2. スコープ: **`workflow`** にチェック
3. 生成されたトークンをコピーしておく（再表示不可）

---

### 3. ロリポップ側のセットアップ

#### 3-1. ファイルをアップロード

ロリポップのファイルマネージャーまたは FTP で、対象ドメインの**公開ディレクトリ**（例: `public_html/`）に以下をアップロードします。

```
deploy/lollipop/
├── api.php        → 公開ディレクトリ直下
├── index.html     → 公開ディレクトリ直下
├── .htaccess      → 公開ディレクトリ直下
└── data/
    ├── .htaccess  → data/ フォルダを作成して中に配置
    └── config.php → data/ フォルダの中に配置
```

#### 3-2. config.php を設定

`data/config.php` を編集して各値を設定します。

```php
// ① Worker 認証キー（フロントエンド・GHA と共有）
define('WORKER_KEY',   'ここを長いランダム文字列に変更');  // ← 必ず変更

// ② GitHub PAT（workflow_dispatch を呼ぶ権限）
define('GITHUB_TOKEN', 'ghp_xxxxxxxxxxxx');               // ← 手順2 で取得したトークン

// ③ リポジトリ名
define('GITHUB_REPO',  'lisso-hookah/edit-videos-poc');   // ← 変更不要（フォークした場合は変更）

// ④ ブランチ名
define('GITHUB_REF',   'main');                           // ← 変更不要
```

> **WORKER_KEY 生成例**: `openssl rand -hex 32`

---

### 4. 使い方

1. ブラウザで `https://your-domain.example.com` を開く
2. 動画ファイル（MP4 / MOV / WAV）をドラッグ＆ドロップ
3. パイプライン（Video / Short / Clip）を選択して設定を入力
4. 「実行する」をクリック → GitHub Actions が自動起動
5. ジョブ一覧でリアルタイムの進捗を確認（5秒ごとに更新）
6. 完了後、「↓ ダウンロード」から処理済み動画を取得

> Actions の起動には数十秒〜数分かかります（ランナーのキュー待ちによる）

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
⑥ 無音カット＋字幕焼き込み  ffmpeg（1 回のエンコードで実行）
⑦ 9:16 縦型変換    ffmpeg（Short のみ）
```

---

## ローカル Worker モード（オプション）

GitHub Actions を使わず、Windows PC をワーカーとして使う場合は `config.php` の `GITHUB_TOKEN` を空にします。

```php
define('GITHUB_TOKEN', '');  // 空にするとローカル Worker モードになる
```

ローカル Worker の起動:

```powershell
# .env に LOLLIPOP_API_URL と WORKER_KEY を設定してから
uv run python scripts\run_worker.py
```

起動すると 5 秒ごとにロリポップへポーリングします。

---

## プロジェクト構成

```
edit-videos-poc/
├── deploy/lollipop/          ← ロリポップにアップロードするファイル
│   ├── api.php               REST API（ジョブ管理・ファイル保管・7日自動削除）
│   ├── index.html            SPA フロントエンド
│   ├── .htaccess             Apache ルーティング設定
│   └── data/
│       ├── .htaccess         data/ への直接アクセスを拒否
│       └── config.php        設定ファイル（WORKER_KEY / GITHUB_TOKEN など）
│
├── start.bat / start.command / start.sh   ローカル起動ランチャー
│
├── src/edit_videos_poc/
│   ├── cli.py                `edit-videos` コマンド（serve / pipeline / short / clip / doctor）
│   ├── config.py             パス・環境変数・既定フォント
│   ├── jobspec.py            ジョブ（パラメータ）→ CLI 引数の変換
│   ├── pipeline/
│   │   ├── _ffmpeg.py        ffmpeg の解決と実行（共通ヘルパー）
│   │   ├── audio.py          音声抽出
│   │   ├── transcribe.py     faster-whisper 文字起こし
│   │   ├── silence.py        無音検出
│   │   ├── refine.py         Gemini フィラー除去
│   │   ├── srt_utils.py      ASS 字幕生成（二重縁取り対応）
│   │   ├── render.py         ffmpeg レンダリング（無音カット + 字幕を 1 パス）
│   │   ├── vertical.py       9:16 縦型変換
│   │   ├── clip.py           切り抜き＋テキスト合成
│   │   └── thumbnail.py      gpt-image-2 サムネイル生成
│   └── web/                  ローカル Web UI（FastAPI）
│       ├── app.py
│       ├── queue_manager.py
│       ├── jobs.py
│       └── static/index.html
│
├── scripts/
│   ├── run_worker.py         Lollipop 連携のローカル Worker（オプション）
│   └── run_*.py              `edit-videos <サブコマンド>` への互換シム（GitHub Actions が使用）
│
├── tests/                    pytest（`uv run --extra dev pytest`）
├── installer/                Windows インストーラー（Inno Setup、uv ベース）
│
├── .github/workflows/
│   ├── run-pipeline.yml      Video Pipeline（Lollipop / 直接 両対応）
│   ├── run-short.yml         Short Pipeline（Lollipop / 直接 両対応）
│   ├── run-clip.yml          Clip Video（Lollipop / 直接 両対応）
│   ├── ci.yml                テスト + Linux / Windows での通し実行
│   └── build-installer.yml   Windows インストーラーのビルド
│
├── .env.example              環境変数テンプレート（ローカル実行時）
├── pyproject.toml / uv.lock  依存定義（uv で管理）
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
- GitHub Actions の処理コストは無料枠（月 2,000 分）で対応
- Lollipop の使用可能ストレージの範囲内で運用
