@echo off
:: Runs the standalone GameInput slot tester INSTEAD of Meridian Launcher.
:: Follow the on-screen prompts - it will ask you to move sticks/press
:: buttons for each vtable slot in turn, up to 40 slots, 5 seconds each.
:: Safe to stop with Ctrl+C and re-run later; it resumes automatically.
::
:: When it finishes (or whenever you stop it), send back:
::   gameinput_slot_test_log.txt
:: from this same folder.

cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
    echo Python wasn't found on PATH. Install Python 3.x and make sure
    echo "python" works from this command prompt, then run this again.
    pause
    exit /b 1
)

python gameinput_slot_test.py
pause
