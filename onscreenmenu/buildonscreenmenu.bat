@echo off
setlocal

REM Builds a single onscreenmenu.exe from this folder.
REM Run install_requirements.bat first if you haven't already.
REM
REM NOT run elevated (--uac-admin removed): Windows actively blocks
REM osk.exe (the on-screen keyboard) from being launched by an
REM elevated process, which broke an earlier version of the
REM Virtual Keyboard option. Combo capture no longer needs a global
REM hook either (it captures keys through its own popup's focus
REM instead). Ctrl+H / Ctrl+T (global hotkeys) still use a keyboard
REM hook, which generally works fine unelevated against ordinary
REM (non-elevated) foreground apps.

pyinstaller ^
    --noconfirm ^
    --onefile ^
    --windowed ^
    --icon onscreenmenu.ico ^
    --name onscreenmenu ^
    launcher.py

echo.
echo Build complete. Find onscreenmenu.exe in the "dist" folder.
pause
