# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec — EditVideos.exe ランチャー
#
# ビルド:  pyinstaller installer\launcher.spec
# 出力:    installer\dist\EditVideos.exe  (約 30 MB)

import sys
from pathlib import Path

block_cipher = None

a = Analysis(
    ['launcher.py'],
    pathex=[str(Path('.').resolve())],
    binaries=[],
    datas=[],
    hiddenimports=[
        # pystray Windows バックエンド
        'pystray._win32',
        'pystray._base',
        # Pillow 内部
        'PIL._imaging',
        'PIL.Image',
        'PIL.ImageDraw',
        'PIL.PngImagePlugin',
        # 標準ライブラリ
        'urllib.request',
        'urllib.error',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # 不要な重い依存を除外
        'torch', 'faster_whisper', 'ctranslate2',
        'google', 'openai', 'fastapi', 'uvicorn',
        'numpy', 'scipy',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='EditVideos',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,          # コンソールウィンドウを表示しない
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.ico',        # BUILD.md の手順で生成
)
