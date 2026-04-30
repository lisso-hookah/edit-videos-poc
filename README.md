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
⑥ 無音カット＋字幕焼き込み  ffmpeg
⑦ 9:16 縦型変換    ffmpeg（Short のみ）
```

---

## コマンドラインから実行（ローカル単体）

Worker を経由せず、直接スクリプトを実行することもできます。

### 必要なもの（ローカル実行時）

| ツール | 用途 |
|---|---|
| Python 3.11+ | ローカル実行 |
| [uv](https://docs.astral.sh/uv/) | Python パッケージ管理 |
| ffmpeg | 動画処理（PATH に追加） |

```powershell
# セットアップ
git clone https://github.com/lisso-hookah/edit-videos-poc.git
cd edit-videos-poc
uv sync
copy .env.example .env  # .env を編集して API キーを設定

# Video Pipeline
uv run python scripts\run_pipeline.py videos\input.mp4 --language ja --font-color yellow

# Short Video Pipeline
uv run python scripts\run_short.py videos\input.mp4 --language ja

# Clip Video
uv run python scripts\run_clip.py videos\input.mp4 --start 10 --end 40 --top-text "タイトル"
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
├── scripts/
│   ├── run_worker.py         Windows ローカル Worker（オプション）
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
│   ├── run-pipeline.yml      Video Pipeline（Lollipop / 直接 両対応）
│   ├── run-short.yml         Short Pipeline（Lollipop / 直接 両対応）
│   └── run-clip.yml          Clip Video（Lollipop / 直接 両対応）
│
├── .env.example              環境変数テンプレート（ローカル実行時）
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
- GitHub Actions の処理コストは無料枠（月 2,000 分）で対応
- Lollipop の使用可能ストレージの範囲内で運用
