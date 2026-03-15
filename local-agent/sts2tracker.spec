# -*- mode: python ; coding: utf-8 -*-
import os
from pathlib import Path

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[str(Path('.').resolve())],
    binaries=[],
    datas=[
        ('assets/icon.ico', 'assets'),
    ],
    hiddenimports=[
        # pystray Windows バックエンド
        'pystray._win32',
        # watchdog Windows バックエンド
        'watchdog.observers.winapi',
        # Pillow イメージフォーマット
        'PIL._tkinter_finder',
        'PIL.Image',
        'PIL.ImageDraw',
        # httpx / httpcore
        'httpcore',
        'httpcore._sync.http11',
        'httpcore._sync.http2',
        'httpcore._async.http11',
        'httpcore._async.http2',
        # sqlite3（offline_queue）
        'sqlite3',
        # python-dotenv
        'dotenv',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'numpy',
        'scipy',
        'pandas',
        'pytest',
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
    name='STS2Tracker',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,          # コンソールウィンドウを非表示（タスクトレイアプリ）
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/icon.ico', # タスクトレイ・exeアイコン
    version_file=None,
    uac_admin=False,
)
