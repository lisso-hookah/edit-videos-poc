# Edit Videos — Windows インストーラーのビルド
#   powershell -ExecutionPolicy Bypass -File installer\build.ps1
# 必要: Inno Setup 6 (https://jrsoftware.org/isdl.php)。出力: installer\dist_installer\EditVideos_Setup_<ver>.exe
$ErrorActionPreference = 'Stop'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path

# 1. 同梱する uv.exe を取得（Python と依存パッケージはインストール時に uv が取得する）
$uvDir = Join-Path $here 'uv'
if (-not (Test-Path (Join-Path $uvDir 'uv.exe'))) {
    $zip = Join-Path $env:TEMP 'uv-x86_64-pc-windows-msvc.zip'
    Invoke-WebRequest 'https://github.com/astral-sh/uv/releases/latest/download/uv-x86_64-pc-windows-msvc.zip' -OutFile $zip
    New-Item -ItemType Directory -Force $uvDir | Out-Null
    Expand-Archive $zip $uvDir -Force
    Remove-Item $zip
}

# 2. Inno Setup でコンパイル
$iscc = @(
    (Get-Command ISCC.exe -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source),
    "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
    "$env:ProgramFiles\Inno Setup 6\ISCC.exe"
) | Where-Object { $_ -and (Test-Path $_) } | Select-Object -First 1
if (-not $iscc) { throw 'ISCC.exe が見つかりません。Inno Setup 6 をインストールしてください。' }

& $iscc (Join-Path $here 'setup.iss')
if ($LASTEXITCODE -ne 0) { throw "ISCC failed ($LASTEXITCODE)" }
Get-ChildItem (Join-Path $here 'dist_installer')
