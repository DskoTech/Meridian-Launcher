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
    --name onscreenmenu ^
    launcher.py

REM osk.bat lives NEXT TO the exe (not bundled inside it), since
REM it's meant to be user-editable - onscreenmenu looks for it in
REM its own exe's folder at runtime. Copy it into dist/ so it's
REM there the moment the exe is.

if exist osk.bat (
    copy /Y osk.bat dist\osk.bat >nul
    echo Copied osk.bat next to the built exe.
) else (
    echo WARNING: osk.bat not found - Start button won't have anything to run.
)

echo.
echo Build complete. Find onscreenmenu.exe (and osk.bat) in the "dist" folder.
pause
