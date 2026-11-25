@echo off
rem Edit Videos - local launcher (Windows). Double-click to start.
rem ASCII only: cmd.exe reads .bat files in the OEM code page.
rem No parenthesised blocks: %PATH% often contains "(x86)", which would end the block early.
setlocal
cd /d "%~dp0"

where uv >nul 2>nul
if not errorlevel 1 goto :run

echo [edit-videos] uv was not found. Installing uv from https://astral.sh/uv ...
powershell -NoProfile -ExecutionPolicy Bypass -Command "irm https://astral.sh/uv/install.ps1 | iex"
if errorlevel 1 goto :fail
set "PATH=%USERPROFILE%\.local\bin;%PATH%"

:run
echo [edit-videos] Starting... the first run downloads Python and the dependencies (a few minutes).
uv run --frozen edit-videos %*
if errorlevel 1 goto :fail
goto :eof

:fail
echo.
echo [edit-videos] Failed to start. See the messages above.
pause
exit /b 1
