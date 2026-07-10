@echo off
setlocal

REM ================================================
REM CyberDeckBrowser Build Script
REM
REM Compiles the project into a standalone Windows
REM executable using PyInstaller.
REM
REM Output: dist\CyberDeckBrowser\CyberDeckBrowser.exe
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
if exist CyberDeckBrowser.spec del /q CyberDeckBrowser.spec

echo.
echo === Building CyberDeckBrowser.exe ===
REM --onedir is used (not --onefile) because
REM QtWebEngine needs its helper process and
REM resource files sitting on disk next to the exe -
REM --onefile's temp-extraction model is unreliable
REM for it.
REM
REM --collect-all PySide6 / shiboken6: PySide6's own
REM DLL-directory setup code needs shiboken6's binaries
REM fully present at a specific relative location. The
REM default PyInstaller hooks don't always grab all of
REM it, which causes an ImportError like:
REM   "...shiboken6\libshiboken does not exist"
REM at startup. Collecting everything from both
REM packages explicitly avoids that.
REM
REM The console window is left VISIBLE for now so
REM startup errors are visible while testing the
REM compiled build. Once you've confirmed it runs
REM correctly, add --windowed to the line below to
REM hide the console for normal use.

pyinstaller --noconfirm --onedir --name CyberDeckBrowser ^
    --icon "icon.ico" ^
    --collect-all PySide6 ^
    --collect-all shiboken6 ^
    --add-data "osk.bat;." ^
    --add-data "icon.ico;." ^
    launcher.py

if errorlevel 1 (
    echo.
    echo Build failed - see the PyInstaller output above.
    pause
    exit /b 1
)

REM Safety net in case --add-data didn't place it
if not exist "dist\CyberDeckBrowser\osk.bat" (
    copy /y "osk.bat" "dist\CyberDeckBrowser\osk.bat" >nul
)

if not exist "dist\CyberDeckBrowser\icon.ico" (
    copy /y "icon.ico" "dist\CyberDeckBrowser\icon.ico" >nul
)

echo.
echo ================================================
echo Build complete.
echo.
echo Your executable is at:
echo   dist\CyberDeckBrowser\CyberDeckBrowser.exe
echo.
echo Run it from that folder (not by moving just the
echo .exe elsewhere) - it needs the rest of the files
echo PyInstaller placed alongside it.
echo ================================================
pause
