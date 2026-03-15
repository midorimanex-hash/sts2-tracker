@echo off
setlocal enabledelayedexpansion

echo ========================================
echo  STS2 Tracker - PyInstaller Build
echo ========================================

:: Check icon file
if not exist "assets\icon.ico" (
    echo [ERROR] assets\icon.ico not found.
    echo         Place icon.ico in local-agent\assets\ before building.
    exit /b 1
)

:: Resolve Python executable
if exist "venv\Scripts\python.exe" (
    set PYTHON=venv\Scripts\python.exe
    set PIP=venv\Scripts\pip.exe
    echo [INFO] Using venv: %PYTHON%
) else (
    echo [WARN] venv not found. Using global Python.
    set PYTHON=python
    set PIP=pip
)

:: Check PyInstaller
if exist "venv\Scripts\pyinstaller.exe" (
    set PYINSTALLER=venv\Scripts\pyinstaller.exe
) else (
    echo [INFO] Installing PyInstaller into venv...
    %PIP% install pyinstaller
    set PYINSTALLER=venv\Scripts\pyinstaller.exe
)

:: Install dependencies
echo [INFO] Installing dependencies...
%PIP% install -r requirements.txt

:: Clean previous build
if exist "dist\STS2Tracker.exe" (
    echo [INFO] Removing previous build...
    del /f "dist\STS2Tracker.exe"
)
if exist "build" (
    rmdir /s /q build
)

:: Build
echo [INFO] Starting build...
%PYINSTALLER% sts2tracker.spec --clean

if errorlevel 1 (
    echo [ERROR] Build failed.
    exit /b 1
)

:: Verify output
if exist "dist\STS2Tracker.exe" (
    echo.
    echo ========================================
    echo  Build succeeded!
    echo  Output: dist\STS2Tracker.exe
    echo ========================================
    for %%A in ("dist\STS2Tracker.exe") do echo  Size: %%~zA bytes
) else (
    echo [ERROR] dist\STS2Tracker.exe was not created.
    exit /b 1
)

endlocal
