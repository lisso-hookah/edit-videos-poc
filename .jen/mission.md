# Mission: ローカルデスクトップアプリ化

## ゴール
GitHub Actions / Lollipop サーバー不要。Python + Tauri でネイティブデスクトップアプリ（.exe / .dmg）として動く形に再構築する。

## 受入条件 (AC)

| # | AC | 状態 |
|---|---|---|
| AC1 | `evp` コマンド（または `python -m edit_videos_poc.web.app`）でローカルサーバーが起動し、ブラウザで動作する | ✅ 実装済 |
| AC2 | フロントエンドが subtitle スタイル選択・位置選択・SVG プレビューを持つ | ✅ 移植済 |
| AC3 | ファイルアップロード → ジョブ送信 → 進捗ポーリング → DL が動く | ✅ API 互換 |
| AC4 | Tauri プロジェクト構造が整い `npm run build` でビルドが走る準備ができている | ✅ 骨格作成済 |
| AC5 | Python サイドカーバイナリを PyInstaller でビルドするスクリプトがある | ✅ build_sidecar.sh |
| AC6 | GHA release.yml で .exe/.dmg をクロスビルドできる | ✅ release.yml |

## 未確認・仮定
- アイコン画像（src-tauri/icons/）はプレースホルダー。本番前に差し替えが必要。
- ffmpeg はユーザー環境にインストール済みと仮定（バンドルしない）。
- Tauri v2 の `tauri-plugin-shell` が sidecar 起動に必要。

## Human Gate
- アイコンデザイン
- App Store / Microsoft Store への提出（署名が必要）
- ffmpeg を同梱するか否かの判断

## 次のステップ
1. `npm install` → `cargo check` でビルドエラーなしを確認
2. アイコンを配置
3. `bash scripts/dev.sh` でブラウザ動作確認
4. `bash scripts/build_app.sh` で初回ビルド
