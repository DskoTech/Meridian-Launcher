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

echo.
echo Cleaning previous build output...
if exist "%SCRIPT_DIR%build" rmdir /s /q "%SCRIPT_DIR%build"
if exist "%SCRIPT_DIR%dist" rmdir /s /q "%SCRIPT_DIR%dist"
if exist "%SCRIPT_DIR%%APP_NAME%.spec" del /q "%SCRIPT_DIR%%APP_NAME%.spec"

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
