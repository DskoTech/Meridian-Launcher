@echo off
REM ============================================================
REM  Meridian Launcher — install_dependencies.bat
REM  Installs everything needed to run from source AND everything
REM  needed to compile it into a Windows .exe (see compile.bat).
REM ============================================================

setlocal

echo.
echo === Meridian Launcher: installing dependencies ===
echo.

where python >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python was not found on PATH. Install Python 3.10+ from
    echo         https://www.python.org/downloads/ and make sure "Add to PATH"
    echo         is checked during setup, then re-run this script.
    goto :end
)

echo Upgrading pip...
python -m pip install --upgrade pip
if errorlevel 1 (
    echo [ERROR] Failed to upgrade pip.
    goto :end
)

echo.
echo Installing requirements.txt (pywebview, mutagen, Pillow, pyinstaller, psutil, pywin32)...
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Failed to install one or more required packages.
    goto :end
)

echo.
echo Running pywin32 post-install fixups (registers COM helpers pywin32 needs)...
python -m pywin32_postinstall -install >nul 2>nul

echo.
echo === Done. ===
echo   - Run "python main.py" to launch Meridian Launcher from source.
echo   - Run "compile.bat" to build Meridian Launcher.exe with PyInstaller.
echo.
echo Optional companion files to drop next to the built .exe:
echo   - CyberDeckBrowser.exe            (Web section)
echo   - Meridian_Explorer.exe           (Files section)
echo   - Meridian Game Library.exe       (Games section "Game Library" entry)

:end
endlocal
pause
