@echo off
setlocal enabledelayedexpansion

rem ============================================================
rem  Build script for Meridian Game Library
rem  Produces a windowed .exe via PyInstaller in --onedir mode.
rem
rem  Why --onedir and not --onefile: --onefile extracts everything
rem  to a fresh temp folder on every launch. This app deliberately
rem  keeps settings.json/keyboard_controls.json/controller_controls.json
rem  next to the exe itself (see store.py) and loads frontend/index.html
rem  from disk — both of those get fragile or reset under --onefile.
rem  --onedir keeps a stable, persistent folder instead. Don't switch
rem  this to --onefile without re-checking store.py's BASE_DIR logic
rem  first.
rem ============================================================

set "APP_NAME=Meridian Game Library"
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

echo ============================================================
echo  Building %APP_NAME%.exe
echo ============================================================
echo.

where python >nul 2>nul
if errorlevel 1 (
    echo Python wasn't found on PATH. Install Python 3.x and make sure
    echo "python" works from this command prompt, then run this again.
    pause
    exit /b 1
)

echo Installing/upgrading build requirements...
python -m pip install --upgrade pip >nul
python -m pip install --upgrade pyinstaller
if errorlevel 1 (
    echo.
    echo Failed to install/upgrade PyInstaller — check your internet
    echo connection and pip setup, then try again.
    pause
    exit /b 1
)

python -m pip install -r "%SCRIPT_DIR%requirements.txt"
if errorlevel 1 (
    echo.
    echo Failed to install one or more requirements from requirements.txt.
    pause
    exit /b 1
)

REM Build the native Rust backend (meridian_core.pyd). BuildMeridianCore.bat
REM lives in the repo root (one level up) and stages the module into THIS
REM folder too. Best-effort: on failure the app falls back to pure Python.
set "CORE_PYD="
if exist "%SCRIPT_DIR%..\BuildMeridianCore.bat" (
    call "%SCRIPT_DIR%..\BuildMeridianCore.bat"
)
if exist "%SCRIPT_DIR%meridian_core.pyd" (
    set "CORE_PYD=1"
    echo Native core present - it will be bundled into the app.
) else (
    echo [WARN] meridian_core.pyd not present - building with pure-Python fallback.
)

REM Stage idle_optimizer.py from repo root (it lives there and is shared
REM by both apps; the GL folder gets its own copy for PyInstaller bundling).
if exist "%SCRIPT_DIR%..\idle_optimizer.py" (
    copy /y "%SCRIPT_DIR%..\idle_optimizer.py" "%SCRIPT_DIR%idle_optimizer.py" >nul
    echo idle_optimizer.py staged.
)

echo.
echo Cleaning previous build output...
if exist "%SCRIPT_DIR%build" rmdir /s /q "%SCRIPT_DIR%build"
if exist "%SCRIPT_DIR%dist" rmdir /s /q "%SCRIPT_DIR%dist"
if exist "%SCRIPT_DIR%%APP_NAME%.spec" del /q "%SCRIPT_DIR%%APP_NAME%.spec"

REM Extra PyInstaller args to bundle the native module, only when it exists.
set "EXTRA_ARGS="
if defined CORE_PYD (
    set EXTRA_ARGS=--add-binary "%SCRIPT_DIR%meridian_core.pyd;." --hidden-import meridian_core
)

echo.
echo Running PyInstaller...
rem --hidden-import win32timezone: a well-known PyInstaller + pywin32 gap —
rem   pywin32 needs it at runtime but PyInstaller's dependency scanner
rem   often misses it, causing a startup crash without this.
rem --collect-submodules webview: makes sure pywebview's platform-specific
rem   backends (edgechromium on Windows) get bundled rather than silently
rem   dropped.
rem --icon: icon.ico ships in this folder already — this sets the .exe's
rem   file icon. Swap in your own icon.ico here if you want a different one.
python -m PyInstaller ^
    --name "%APP_NAME%" ^
    --windowed ^
    --onedir ^
    --contents-directory "MeridianGameLibrary_internal" ^
    --noconfirm ^
    --hidden-import win32timezone ^
    --collect-submodules webview ^
    --add-data "%SCRIPT_DIR%idle_optimizer.py;." ^
    --exclude-module PySide6 --exclude-module PyQt5 --exclude-module PyQt6 ^
    --exclude-module shiboken6 --exclude-module pygame ^
    --exclude-module numpy --exclude-module matplotlib ^
    --exclude-module scipy --exclude-module pandas ^
    --exclude-module tkinter --exclude-module _tkinter --exclude-module test ^
    !EXTRA_ARGS! ^
    --icon "%SCRIPT_DIR%icon.ico" ^
    "%SCRIPT_DIR%main.py"

if errorlevel 1 (
    echo.
    echo ============================================================
    echo  Build FAILED — scroll up for the actual PyInstaller error.
    echo ============================================================
    pause
    exit /b 1
)

echo.
echo Copying the frontend folder next to the built exe...
xcopy /e /i /y "%SCRIPT_DIR%frontend" "%SCRIPT_DIR%dist\%APP_NAME%\frontend" >nul

echo.
echo ============================================================
echo  Done. Find it at:
echo    dist\%APP_NAME%\%APP_NAME%.exe
echo.
echo  First run will create settings.json, keyboard_controls.json,
echo  and controller_controls.json next to the exe automatically.
echo ============================================================
pause
