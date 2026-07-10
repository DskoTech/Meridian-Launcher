@echo off
setlocal

REM ================================================
REM CyberBrowser Build Script
REM
REM Compiles the project into a standalone Windows
REM executable using PyInstaller.
REM
REM Output: dist\CyberBrowser\CyberBrowser.exe
REM ================================================

cd /d "%~dp0"

echo.
echo === Installing/upgrading build tools ===
python -m pip install --upgrade pyinstaller pyinstaller-hooks-contrib
if errorlevel 1 (
    echo.
    echo Failed to install PyInstaller. Make sure Python
    echo and pip are installed and available on PATH.
    pause
    exit /b 1
)

echo.
echo === Installing app dependencies ===
python -m pip install -r Requirements.txt
if errorlevel 1 (
    echo.
    echo Failed to install dependencies from Requirements.txt.
    pause
    exit /b 1
)

echo.
echo === Cleaning previous build ===
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist CyberBrowser.spec del /q CyberBrowser.spec

echo.
echo === Building CyberBrowser.exe ===
REM --onedir is used (not --onefile) because
REM QtWebEngine needs its helper process and
REM resource files sitting on disk next to the exe -
REM --onefile's temp-extraction model is unreliable
REM for it.
REM
REM The console window is left VISIBLE for now so
REM startup errors are visible while testing the
REM compiled build. Once you've confirmed it runs
REM correctly, add --windowed to the line below to
REM hide the console for normal use.

pyinstaller --noconfirm --onedir --name CyberBrowser --add-data "osk.bat;." launcher.py

if errorlevel 1 (
    echo.
    echo Build failed - see the PyInstaller output above.
    pause
    exit /b 1
)

REM Safety net in case --add-data didn't place it
if not exist "dist\CyberBrowser\osk.bat" (
    copy /y "osk.bat" "dist\CyberBrowser\osk.bat" >nul
)

echo.
echo ================================================
echo Build complete.
echo.
echo Your executable is at:
echo   dist\CyberBrowser\CyberBrowser.exe
echo.
echo Run it from that folder (not by moving just the
echo .exe elsewhere) - it needs the rest of the files
echo PyInstaller placed alongside it.
echo ================================================
pause
