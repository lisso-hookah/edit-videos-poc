<?php
/**
 * 設定ファイル — data/ に置くことで HTTP 直接アクセスを遮断
 *
 * ① WORKER_KEY  : フロントエンドと GitHub Actions が共有する認証キー
 * ② GITHUB_TOKEN: workflow_dispatch を呼ぶ GitHub PAT
 *    取得: https://github.com/settings/tokens
 *    必要スコープ: repo（または workflow）
 * ③ GITHUB_REPO : "owner/repo" 形式
 */

// ── 必須設定 ──────────────────────────────────────────────────
define('WORKER_KEY',    'CHANGE_ME_worker_secret_key');  // ← 必ず変更

// ── GitHub Actions 連携（フル Lollipop モード用） ─────────────
define('GITHUB_TOKEN',  '');                             // ← GitHub PAT を設定
define('GITHUB_REPO',   'lisso-hookah/edit-videos-poc'); // ← リポジトリ名
define('GITHUB_REF',    'main');                         // ← ブランチ名
