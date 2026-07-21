@echo off
setlocal

REM ================================================
REM Meridian NetBrowse Shell Handler - Build Script
REM
REM NOTE: this used to also build a full standalone "Meridian
REM NetBrowse.exe" (from launcher.py + the rest of this folder's
REM browser/controller/cursor/etc code) - that's now obsolete.
REM CyberDeckBrowser absorbed everything Meridian NetBrowse did via its
REM own --box=X,Y,W,H argument (see CyberDeckBrowser/main.py's module
REM docstring), so Meridian Launcher's Browser section now launches
REM CyberDeckBrowser.exe boxed instead of a separate NetBrowse.exe. The
REM old engine's source has been moved to
REM ../obsolete/Meridian_NetBrowse_LegacyEngine/ rather than deleted -
REM see ../obsolete/README.md.
REM
REM What's LEFT in this folder and still genuinely needed:
REM netbrowse_shell_handler.py - a tiny, fully self-contained trampoline
REM (stdlib only, no dependency on anything else in this folder) that
REM Windows invokes as the registered default web browser; its only job
REM is handing the URL to an already-running Meridian Launcher. This
REM script builds ONLY that.
REM
REM Output: Meridian NetBrowse Shell Handler.exe (single file)
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
echo === Cleaning previous build ===
if exist build_trampoline rmdir /s /q build_trampoline
if exist "Meridian NetBrowse Shell Handler.spec" del /q "Meridian NetBrowse Shell Handler.spec"

echo.
echo Building the "default system web browser" trampoline...
pyinstaller --noconfirm --onefile --windowed --distpath . --workpath build_trampoline ^
    --name "Meridian NetBrowse Shell Handler" ^
    netbrowse_shell_handler.py

if errorlevel 1 (
    echo.
    echo ============================================================
    echo  Trampoline build FAILED - the "Make default system web
    echo  browser" macro/setting won't be offered until this is built.
    echo ============================================================
    pause
    exit /b 1
)

echo.
echo ================================================
echo Build complete.
echo.
echo Your executable is at:
echo   Meridian NetBrowse Shell Handler.exe  (only needed for the
echo     "Make Meridian NetBrowse the default system web browser" setting)
echo.
echo Copy it to wherever Meridian Launcher.exe lives.
echo ================================================
pause
