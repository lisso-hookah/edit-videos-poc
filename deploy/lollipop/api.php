<?php
/**
 * Edit Videos – Lollipop API
 *
 * フロントエンドとローカル Worker の両方が使う REST API。
 * データベース不要・JSONファイルで状態管理。
 *
 * ─── 設定 ──────────────────────────────────────────────────────
 */
define('WORKER_KEY',     'CHANGE_ME_worker_secret_key');  // ← 必ず変更する
define('DATA_DIR',       __DIR__ . '/data');
define('JOBS_DIR',       DATA_DIR . '/jobs');
define('UPLOADS_DIR',    DATA_DIR . '/uploads');
define('RESULTS_DIR',    DATA_DIR . '/results');
define('RETENTION_DAYS', 7);
define('STALE_HOURS',    2);   // running のまま N 時間経過したら再キュー

// ─── 初期化 ─────────────────────────────────────────────────────
foreach ([JOBS_DIR, UPLOADS_DIR, RESULTS_DIR] as $dir) {
    if (!is_dir($dir)) {
        mkdir($dir, 0755, true);
    }
}

// ─── ルーティング ────────────────────────────────────────────────
$method = $_SERVER['REQUEST_METHOD'];
$uri    = parse_url($_SERVER['REQUEST_URI'], PHP_URL_PATH);
$uri    = '/' . ltrim(preg_replace('#^/api#', '', $uri), '/');

// 古いファイルを定期削除（リクエストのたびに確率的に実行）
if (mt_rand(0, 19) === 0) {
    cleanup_old_files();
}

// ブラウザ向け
if ($method === 'POST' && $uri === '/upload') {
    handle_upload();
}
if ($method === 'POST' && $uri === '/jobs') {
    handle_submit_job();
}
if ($method === 'GET' && $uri === '/jobs') {
    handle_list_jobs();
}
if ($method === 'GET' && preg_match('#^/jobs/([^/]+)/download$#', $uri, $m)) {
    handle_download($m[1]);
}

// Worker 向け（API キー必須）
if ($method === 'GET' && $uri === '/worker/jobs/next') {
    require_worker_key();
    worker_next_job();
}
if ($method === 'GET' && preg_match('#^/worker/uploads/([^/]+)$#', $uri, $m)) {
    require_worker_key();
    worker_download_upload($m[1]);
}
if ($method === 'POST' && preg_match('#^/worker/jobs/([^/]+)/progress$#', $uri, $m)) {
    require_worker_key();
    worker_update_progress($m[1]);
}
if ($method === 'POST' && preg_match('#^/worker/jobs/([^/]+)/complete$#', $uri, $m)) {
    require_worker_key();
    worker_complete_job($m[1]);
}
if ($method === 'POST' && preg_match('#^/worker/jobs/([^/]+)/fail$#', $uri, $m)) {
    require_worker_key();
    worker_fail_job($m[1]);
}

json_response(['error' => 'Not Found'], 404);

// ════════════════════════════════════════════════════════════════
// ブラウザ向けハンドラ
// ════════════════════════════════════════════════════════════════

function handle_upload(): never
{
    if (!isset($_FILES['file']) || $_FILES['file']['error'] !== UPLOAD_ERR_OK) {
        json_response(['error' => 'ファイルのアップロードに失敗しました'], 400);
    }

    $file     = $_FILES['file'];
    $ext      = strtolower(pathinfo($file['name'], PATHINFO_EXTENSION));
    $allowed  = ['mp4', 'mov', 'wav', 'mp3', 'm4a'];
    if (!in_array($ext, $allowed, true)) {
        json_response(['error' => '対応していない形式です (mp4/mov/wav)'], 400);
    }

    $file_id  = make_id();
    $dest     = UPLOADS_DIR . "/{$file_id}.{$ext}";
    if (!move_uploaded_file($file['tmp_name'], $dest)) {
        json_response(['error' => '保存に失敗しました'], 500);
    }

    json_response([
        'file_id'  => $file_id,
        'filename' => $file['name'],
        'size'     => $file['size'],
        'ext'      => $ext,
    ]);
}

function handle_submit_job(): never
{
    $body     = json_body();
    $pipeline = $body['pipeline'] ?? '';
    $file_id  = $body['file_id']  ?? '';
    $params   = $body['params']   ?? [];

    if (!in_array($pipeline, ['pipeline', 'short', 'clip'], true) || $file_id === '') {
        json_response(['error' => '必須パラメーターが不正です'], 400);
    }

    // アップロードファイルを確認
    $upload = find_upload($file_id);
    if ($upload === null) {
        json_response(['error' => 'アップロードファイルが見つかりません'], 404);
    }

    $job = [
        'id'               => make_id(),
        'pipeline'         => $pipeline,
        'params'           => $params,
        'file_id'          => $file_id,
        'file_ext'         => $upload['ext'],
        'status'           => 'queued',
        'progress'         => 0,
        'progress_label'   => '待機中',
        'error'            => null,
        'created_at'       => date('c'),
        'worker_claimed_at'=> null,
    ];

    save_job($job);
    json_response(['job_id' => $job['id'], 'status' => 'queued'], 201);
}

function handle_list_jobs(): never
{
    $jobs = load_all_jobs();
    // 新しい順
    usort($jobs, fn($a, $b) => strcmp($b['created_at'], $a['created_at']));

    $result = array_map(fn($j) => [
        'id'             => $j['id'],
        'pipeline'       => $j['pipeline'],
        'status'         => $j['status'],
        'progress'       => $j['progress'],
        'progress_label' => $j['progress_label'],
        'error'          => $j['error'],
        'has_result'     => file_exists(RESULTS_DIR . "/{$j['id']}.mp4"),
        'created_at'     => $j['created_at'],
    ], $jobs);

    json_response($result);
}

function handle_download(string $job_id): never
{
    $job = load_job($job_id);
    if ($job === null || $job['status'] !== 'done') {
        json_response(['error' => '結果が見つかりません'], 404);
    }

    $path = RESULTS_DIR . "/{$job_id}.mp4";
    if (!file_exists($path)) {
        json_response(['error' => 'ファイルが見つかりません'], 404);
    }

    $name = basename($path);
    header('Content-Type: video/mp4');
    header('Content-Disposition: attachment; filename="' . $name . '"');
    header('Content-Length: ' . filesize($path));
    header('Cache-Control: no-cache');
    readfile($path);
    exit;
}

// ════════════════════════════════════════════════════════════════
// Worker 向けハンドラ
// ════════════════════════════════════════════════════════════════

function worker_next_job(): never
{
    // stale な running ジョブをキューに戻す
    recover_stale_jobs();

    $lock = fopen(DATA_DIR . '/queue.lock', 'c');
    if (!flock($lock, LOCK_EX)) {
        json_response(null);
    }

    $jobs = load_all_jobs();
    usort($jobs, fn($a, $b) => strcmp($a['created_at'], $b['created_at']));

    $claimed = null;
    foreach ($jobs as $j) {
        if ($j['status'] === 'queued') {
            $j['status']            = 'running';
            $j['progress']          = 0;
            $j['progress_label']    = '開始中';
            $j['worker_claimed_at'] = date('c');
            save_job($j);
            $claimed = $j;
            break;
        }
    }

    flock($lock, LOCK_UN);
    fclose($lock);

    if ($claimed === null) {
        json_response(null);
    }

    $upload = find_upload($claimed['file_id']);
    json_response([
        'job_id'       => $claimed['id'],
        'pipeline'     => $claimed['pipeline'],
        'params'       => $claimed['params'],
        'download_url' => '/api/worker/uploads/' . $claimed['file_id'],
    ]);
}

function worker_download_upload(string $file_id): never
{
    $upload = find_upload($file_id);
    if ($upload === null) {
        json_response(['error' => 'Not Found'], 404);
    }

    $path = $upload['path'];
    $ext  = strtolower(pathinfo($path, PATHINFO_EXTENSION));
    $mime = ($ext === 'wav' || $ext === 'mp3' || $ext === 'm4a') ? 'audio/mpeg' : 'video/mp4';

    header("Content-Type: {$mime}");
    header('Content-Disposition: attachment; filename="upload.' . $ext . '"');
    header('Content-Length: ' . filesize($path));
    readfile($path);
    exit;
}

function worker_update_progress(string $job_id): never
{
    $job = load_job($job_id);
    if ($job === null) {
        json_response(['error' => 'Not Found'], 404);
    }

    $body = json_body();
    $job['progress']       = (int)($body['progress'] ?? $job['progress']);
    $job['progress_label'] = (string)($body['progress_label'] ?? $job['progress_label']);
    save_job($job);

    json_response(['ok' => true]);
}

function worker_complete_job(string $job_id): never
{
    $job = load_job($job_id);
    if ($job === null) {
        json_response(['error' => 'Not Found'], 404);
    }

    if (!isset($_FILES['file']) || $_FILES['file']['error'] !== UPLOAD_ERR_OK) {
        json_response(['error' => '結果ファイルのアップロードに失敗しました'], 400);
    }

    $dest = RESULTS_DIR . "/{$job_id}.mp4";
    if (!move_uploaded_file($_FILES['file']['tmp_name'], $dest)) {
        json_response(['error' => '保存に失敗しました'], 500);
    }

    $job['status']         = 'done';
    $job['progress']       = 100;
    $job['progress_label'] = '完了';
    save_job($job);

    json_response(['ok' => true]);
}

function worker_fail_job(string $job_id): never
{
    $job = load_job($job_id);
    if ($job === null) {
        json_response(['error' => 'Not Found'], 404);
    }

    $body = json_body();
    $job['status']         = 'failed';
    $job['progress_label'] = '失敗';
    $job['error']          = (string)($body['error'] ?? '不明なエラー');
    save_job($job);

    json_response(['ok' => true]);
}

// ════════════════════════════════════════════════════════════════
// ユーティリティ
// ════════════════════════════════════════════════════════════════

function make_id(): string
{
    return bin2hex(random_bytes(16));
}

function json_body(): array
{
    $raw = file_get_contents('php://input');
    return json_decode($raw, true) ?? [];
}

function json_response(mixed $data, int $code = 200): never
{
    http_response_code($code);
    header('Content-Type: application/json; charset=utf-8');
    echo json_encode($data, JSON_UNESCAPED_UNICODE);
    exit;
}

function require_worker_key(): void
{
    $key = $_SERVER['HTTP_X_WORKER_KEY'] ?? '';
    if (!hash_equals(WORKER_KEY, $key)) {
        json_response(['error' => 'Unauthorized'], 401);
    }
}

function save_job(array $job): void
{
    $path = JOBS_DIR . "/{$job['id']}.json";
    file_put_contents($path, json_encode($job, JSON_UNESCAPED_UNICODE | JSON_PRETTY_PRINT), LOCK_EX);
}

function load_job(string $id): ?array
{
    $path = JOBS_DIR . "/{$id}.json";
    if (!file_exists($path)) {
        return null;
    }
    $data = json_decode(file_get_contents($path), true);
    return is_array($data) ? $data : null;
}

function load_all_jobs(): array
{
    $jobs = [];
    foreach (glob(JOBS_DIR . '/*.json') as $file) {
        $data = json_decode(file_get_contents($file), true);
        if (is_array($data)) {
            $jobs[] = $data;
        }
    }
    return $jobs;
}

function find_upload(string $file_id): ?array
{
    foreach (glob(UPLOADS_DIR . '/' . $file_id . '.*') as $path) {
        return ['path' => $path, 'ext' => pathinfo($path, PATHINFO_EXTENSION)];
    }
    return null;
}

function recover_stale_jobs(): void
{
    $threshold = time() - STALE_HOURS * 3600;
    foreach (load_all_jobs() as $j) {
        if ($j['status'] !== 'running') {
            continue;
        }
        $claimed = $j['worker_claimed_at'] ? strtotime($j['worker_claimed_at']) : 0;
        if ($claimed < $threshold) {
            $j['status']            = 'queued';
            $j['progress']          = 0;
            $j['progress_label']    = '待機中（再試行）';
            $j['worker_claimed_at'] = null;
            save_job($j);
        }
    }
}

function cleanup_old_files(): void
{
    $threshold = time() - RETENTION_DAYS * 86400;

    // 古いジョブとその関連ファイルを削除
    foreach (load_all_jobs() as $j) {
        if (strtotime($j['created_at']) < $threshold) {
            @unlink(JOBS_DIR   . "/{$j['id']}.json");
            @unlink(RESULTS_DIR . "/{$j['id']}.mp4");
        }
    }

    // 古いアップロードファイルを削除
    foreach (glob(UPLOADS_DIR . '/*') as $file) {
        if (filemtime($file) < $threshold) {
            @unlink($file);
        }
    }
}
