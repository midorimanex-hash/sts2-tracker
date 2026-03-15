@echo off
setlocal enabledelayedexpansion

echo ========================================
echo  STS2 Tracker - PyInstaller Build
echo ========================================

:: assetsディレクトリの確認
if not exist "assets\icon.ico" (
    echo [ERROR] assets\icon.ico が見つかりません。
    echo         icon.ico を local-agent\assets\ に配置してください。
    exit /b 1
)

:: venv の確認・アクティベート
if exist "venv\Scripts\activate.bat" (
    echo [INFO] venv をアクティベートします...
    call venv\Scripts\activate.bat
) else (
    echo [WARN] venv が見つかりません。グローバル Python を使用します。
)

:: PyInstaller のインストール確認
python -m pyinstaller --version >nul 2>&1
if errorlevel 1 (
    echo [INFO] PyInstaller をインストールします...
    pip install pyinstaller
)

:: 依存パッケージのインストール
echo [INFO] 依存パッケージをインストールします...
pip install -r requirements.txt

:: 前回のビルド成果物を削除
if exist "dist\STS2Tracker.exe" (
    echo [INFO] 前回のビルドを削除します...
    del /f "dist\STS2Tracker.exe"
)
if exist "build" (
    rmdir /s /q build
)

:: ビルド実行
echo [INFO] ビルドを開始します...
python -m pyinstaller sts2tracker.spec --clean

if errorlevel 1 (
    echo [ERROR] ビルドに失敗しました。
    exit /b 1
)

:: 成果物の確認
if exist "dist\STS2Tracker.exe" (
    echo.
    echo ========================================
    echo  ビルド成功！
    echo  出力: dist\STS2Tracker.exe
    echo ========================================
    for %%A in ("dist\STS2Tracker.exe") do echo  サイズ: %%~zA bytes
) else (
    echo [ERROR] dist\STS2Tracker.exe が生成されませんでした。
    exit /b 1
)

endlocal
