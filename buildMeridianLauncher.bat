@echo off
REM ============================================================
REM  MeridianLauncher — compile.bat
REM  Compiles main.py + frontend/ into a single-file Windows .exe
REM  using meridian.spec. Run install_dependencies.bat first if
REM  you haven't already.
REM ============================================================

setlocal

echo.
echo === MeridianLauncher: compiling to Windows .exe ===
echo.

where python >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python was not found on PATH. Run install_dependencies.bat first.
    goto :end
)

python -c "import PyInstaller" >nul 2>nul
if errorlevel 1 (
    echo [ERROR] PyInstaller isn't installed. Run install_dependencies.bat first.
    goto :end
)

echo Cleaning previous build output...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

echo.
echo Building with PyInstaller (meridian.spec)...
python -m PyInstaller meridian.spec --noconfirm
if errorlevel 1 (
    echo [ERROR] Build failed — see the PyInstaller output above.
    goto :end
)

echo.
echo === Build complete ===
echo   dist\MeridianLauncher.exe
echo.
echo Remember: settings.json, keyboard_controls.json, and
echo controller_controls.json are generated next to the .exe on first
echo run, so they are NOT bundled. Drop any of these next to the .exe
echo if you want them: CyberDeckBrowser.exe,
echo Meridian_Explorer.exe, "Meridian Game Library.exe".

:end
endlocal
pause
