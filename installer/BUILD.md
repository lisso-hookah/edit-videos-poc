# Edit Videos — Windows インストーラー ビルド手順

`EditVideos_Setup_1.0.0.exe` を作成するための手順書です。  
Windows 11 / 10 (x64) 環境で実施してください。

---

## 必要なツール（ビルドマシン）

| ツール | バージョン | 入手先 |
|--------|-----------|--------|
| Python | 3.11 以上 | https://python.org |
| Inno Setup | 6.x | https://jrsoftware.org/isdl.php |
| Git | 最新 | https://git-scm.com |

---

## Step 1 — リポジトリのクローン

```powershell
git clone https://github.com/lisso-hookah/edit-videos-poc.git
cd edit-videos-poc
```

---

## Step 2 — ランチャービルド用ライブラリのインストール

```powershell
pip install pyinstaller pystray pillow
```

---

## Step 3 — アイコンの生成

```powershell
python installer\create_icon.py
# → installer\icon.ico が生成される
```

---

## Step 4 — Python 3.11 embeddable のダウンロード・展開

```powershell
# ダウンロード
curl -Lo installer\python-3.11.9-embed-amd64.zip `
  https://www.python.org/ftp/python/3.11.9/python-3.11.9-embed-amd64.zip

# 展開先を作成
mkdir installer\python-embed

# 展開
Expand-Archive installer\python-3.11.9-embed-amd64.zip installer\python-embed
```

---

## Step 5 — get-pip.py のダウンロード

```powershell
curl -Lo installer\get-pip.py https://bootstrap.pypa.io/get-pip.py
```

---

## Step 6 — ffmpeg バイナリのダウンロード

[https://www.gyan.dev/ffmpeg/builds/](https://www.gyan.dev/ffmpeg/builds/) から
`ffmpeg-release-essentials.zip` をダウンロードし、中の `ffmpeg.exe` と `ffprobe.exe` だけを取り出す。

```powershell
mkdir installer\ffmpeg-bin

# ダウンロード（バージョンは適宜変更）
curl -Lo installer\ffmpeg.zip `
  https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip

# 展開して EXE だけコピー（フォルダ名はバージョンにより異なる）
Expand-Archive installer\ffmpeg.zip installer\ffmpeg-tmp
Copy-Item installer\ffmpeg-tmp\ffmpeg-*\bin\ffmpeg.exe  installer\ffmpeg-bin\
Copy-Item installer\ffmpeg-tmp\ffmpeg-*\bin\ffprobe.exe installer\ffmpeg-bin\
Remove-Item installer\ffmpeg-tmp -Recurse
```

---

## Step 7 — ランチャー EXE のビルド（PyInstaller）

```powershell
# リポジトリルートから実行
pyinstaller installer\launcher.spec

# → installer\dist\EditVideos.exe が生成される（約 25〜35 MB）
```

---

## Step 8 — installer フォルダの構成確認

ビルド前に以下がすべて揃っていることを確認してください。

```
installer\
├── dist\
│   └── EditVideos.exe          ← Step 7 で生成
├── python-embed\               ← Step 4 で展開
│   ├── python.exe
│   ├── pythonw.exe
│   ├── python311.zip
│   ├── python311._pth
│   └── ... (他の DLL 等)
├── ffmpeg-bin\                 ← Step 6 でコピー
│   ├── ffmpeg.exe
│   └── ffprobe.exe
├── get-pip.py                  ← Step 5 でダウンロード
├── icon.ico                    ← Step 3 で生成
├── setup_env.py                ← リポジトリに含まれる
├── setup.iss                   ← リポジトリに含まれる
└── launcher.spec               ← リポジトリに含まれる
```

---

## Step 9 — Inno Setup でインストーラーをビルド

**GUI の場合:**
1. Inno Setup を起動
2. `installer\setup.iss` を開く
3. **Build → Compile** (Ctrl+F9)
4. `installer\dist_installer\EditVideos_Setup_1.0.0.exe` が生成される

**コマンドラインの場合:**
```powershell
# Inno Setup のパスは環境に合わせて変更
& "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer\setup.iss
```

---

## インストーラーの動作

```
ユーザーが EditVideos_Setup_1.0.0.exe を実行
  │
  ├─ インストール先の選択（デフォルト: C:\Program Files\EditVideos\）
  ├─ ショートカットの設定
  ├─ API キーの入力（Gemini / OpenAI / Whisper モデル選択）
  ├─ ファイルのコピー
  │     EditVideos.exe, Python 3.11, ffmpeg, ソースコード
  ├─ Python 環境セットアップ（インターネット接続が必要）
  │     pip のインストール → 依存パッケージのインストール（約 300〜500 MB）
  └─ 完了 → EditVideos を起動するか選択

EditVideos.exe を起動
  │
  ├─ FastAPI サーバーをバックグラウンドで起動
  ├─ http://127.0.0.1:8000 が開くのを待つ
  ├─ 既定ブラウザで自動的に開く
  └─ システムトレイアイコン表示
       右クリック → 「ブラウザで開く」 / 「終了」
```

---

## 注意事項

| 項目 | 内容 |
|------|------|
| インストール時のインターネット | Python パッケージのダウンロードに必要（約 300〜500 MB） |
| Whisper モデル | 初回使用時に自動ダウンロード（medium: 約 1.5 GB、large-v3: 約 3 GB） |
| GPU なし | CPU で動作するが文字起こしが遅くなる（medium なら数分〜十数分） |
| GPU あり (NVIDIA) | CUDA 対応の ctranslate2 を追加インストールで大幅高速化 |
| アンインストール | コントロールパネル → プログラムの追加と削除 から実施 |

---

## トラブルシューティング

**「パッケージのインストールに失敗した」**
- インターネット接続を確認し、再インストールを試す
- ウイルス対策ソフトが pip をブロックしていないか確認

**「EditVideos.exe を起動しても何も起きない」**
- `{インストール先}\logs\` に出力がある場合は確認する
- Python が正しくセットアップされているか: `{インストール先}\python\python.exe --version`

**「ブラウザが開かない」**
- 直接 http://127.0.0.1:8000 にアクセスしてみる
- ファイアウォールがポート 8000 をブロックしていないか確認
