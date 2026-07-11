@echo off
setlocal

REM ============================================================
REM  Build script for Meridian Explorer
REM  Produces a single-file windowed .exe via PyInstaller.
REM ============================================================

cd /d "%~dp0"

echo ============================================================
echo  Building Meridian Explorer.exe
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
python -m pip install --upgrade pygame pyinstaller
if errorlevel 1 (
    echo.
    echo Failed to install/upgrade pygame/PyInstaller - check your internet
    echo connection and pip setup, then try again.
    pause
    exit /b 1
)

echo.
echo Cleaning previous build output...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist "Meridian Explorer.spec" del /q "Meridian Explorer.spec"

echo.
echo Running PyInstaller...
pyinstaller --noconfirm --onefile --windowed ^
    --icon "Meridian_Explorer.ico" ^
    --name "Meridian Explorer" ^
    Meridian_Explorer.py

if errorlevel 1 (
    echo.
    echo ============================================================
    echo  Build FAILED - scroll up for the actual PyInstaller error.
    echo ============================================================
    pause
    exit /b 1
)

echo.
echo ============================================================
echo  Done. Find it at:
echo    dist\Meridian Explorer.exe
echo ============================================================
pause
