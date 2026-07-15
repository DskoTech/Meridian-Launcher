@echo off
setlocal

REM ============================================================
REM  Build script for Meridian FileBrowse
REM  (the Explorer-section-embedded fork of Meridian Explorer)
REM  Produces a single-file windowed .exe via PyInstaller.
REM ============================================================

cd /d "%~dp0"

echo ============================================================
echo  Building Meridian FileBrowse.exe
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
if exist "Meridian FileBrowse.spec" del /q "Meridian FileBrowse.spec"

echo.
echo Running PyInstaller...
pyinstaller --noconfirm --onefile --windowed ^
    --name "Meridian FileBrowse" ^
    MeridianFileBrowse.py

if errorlevel 1 (
    echo.
    echo ============================================================
    echo  Build FAILED - scroll up for the actual PyInstaller error.
    echo ============================================================
    pause
    exit /b 1
)

echo.
echo Building the "default shell browser" trampoline...
pyinstaller --noconfirm --onefile --windowed ^
    --name "Meridian FileBrowse Shell Handler" ^
    filebrowse_shell_handler.py

if errorlevel 1 (
    echo.
    echo ============================================================
    echo  Trampoline build FAILED - Meridian FileBrowse.exe itself is
    echo  still fine; the "Make default shell browser" macro just won't
    echo  be offered until this is built too.
    echo ============================================================
    pause
    exit /b 1
)

echo.
echo ============================================================
echo  Done. Find them at:
echo    dist\Meridian FileBrowse.exe
echo    dist\Meridian FileBrowse Shell Handler.exe
echo  Copy both next to Meridian Launcher.exe - the first is what the
echo  Explorer section loads; the second is only needed if you use the
echo  "Make Meridian FileBrowse the default shell browser" setting.
echo ============================================================
pause
