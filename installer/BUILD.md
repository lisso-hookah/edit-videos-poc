# Edit Videos — Windows インストーラー

> ふだん使うだけならインストーラーは不要です。リポジトリを取得して `start.bat` をダブルクリックすれば起動します（README 参照）。
> インストーラーは「スタートメニューに登録したい」「API キーをウィザードで入力させたい」場合の配布用です。

## 仕組み

インストーラーに入っているのは **`uv.exe` とソースコードだけ**（数十 MB）です。

```
EditVideos_Setup_<ver>.exe を実行
  ├─ インストール先（既定: %LOCALAPPDATA%\Programs\EditVideos、管理者権限不要）
  ├─ API キー / Whisper モデルの入力 → {インストール先}\.env
  ├─ uv sync --frozen … uv.lock どおりに Python 本体と依存パッケージを取得（要インターネット）
  └─ ショートカット → start.bat（コンソールが開き、ブラウザで http://127.0.0.1:8000 が開く）
```

- 依存パッケージの一覧は `pyproject.toml` / `uv.lock` だけが正です（インストーラー側に重複した一覧はありません）
- ffmpeg は依存パッケージ（imageio-ffmpeg）に含まれるため、別途同梱しません
- 終了はコンソールウィンドウを閉じるか Ctrl+C

## ビルド

必要: Windows 10/11 x64、[Inno Setup 6](https://jrsoftware.org/isdl.php)

```powershell
powershell -ExecutionPolicy Bypass -File installer\build.ps1
# → installer\dist_installer\EditVideos_Setup_<ver>.exe
```

GitHub Actions でもビルドできます: **Actions → Build Windows installer → Run workflow**（成果物 `EditVideos_Setup` がダウンロードできます）。

## トラブルシューティング

| 症状 | 対処 |
|---|---|
| インストール中の取得に失敗した | ネットワークを確認して `start.bat` を実行（不足分を取得し直します） |
| 起動しない / ジョブが失敗する | インストール先でコマンドプロンプトを開き `uv run --frozen edit-videos doctor` |
| ポート 8000 が使用中 | `start.bat --port 8001` |
