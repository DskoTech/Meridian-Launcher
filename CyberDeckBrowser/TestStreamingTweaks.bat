@echo off
setlocal enabledelayedexpansion

REM ============================================================
REM  Test each CyberDeckBrowser streaming/login tweak individually
REM
REM  Run this from wherever CyberDeckBrowser.exe actually lives
REM  (e.g. C:\Program Files\DskoTech\) - it launches the SAME exe
REM  with one env var set at a time so you can bisect which change
REM  is causing pages to load blank. See CyberDeckBrowser/main.py's
REM  _configure_streaming_playback / _configure_persistent_web_profile
REM  docstrings for exactly what each one does.
REM ============================================================

if not exist "%~dp0CyberDeckBrowser.exe" (
    echo [ERROR] CyberDeckBrowser.exe not found next to this script.
    echo Copy this .bat next to it first ^(e.g. C:\Program Files\DskoTech\^).
    pause
    exit /b 1
)

:menu
cls
echo ============================================================
echo  CyberDeckBrowser streaming/login tweak tester
echo ============================================================
echo.
echo  Each option launches CyberDeckBrowser.exe standalone with ONE
echo  tweak disabled. Close the window when done testing, then pick
echo  the next one. If a specific option fixes the blank-page issue,
echo  that tweak is the culprit.
echo.
echo  1. Disable Widevine flags        (--widevine-path / --ppapi-widevine-path)
echo  2. Disable autoplay flag         (--autoplay-policy)
echo  3. Disable profile persistence   (org/app name, storage path, cookie policy)
echo  4. Disable User-Agent override
echo  5. Disable plugins/playback flags (PluginsEnabled etc.)
echo  6. Disable ALL FIVE at once      (should behave like the pre-tweak build)
echo  7. Run normally (all tweaks ON, for comparison)
echo  Q. Quit
echo.
set /p CHOICE="Pick an option: "

if /i "%CHOICE%"=="1" (
    set "MERIDIAN_DISABLE_WIDEVINE_FLAGS=1"
    "%~dp0CyberDeckBrowser.exe"
    set "MERIDIAN_DISABLE_WIDEVINE_FLAGS="
    goto menu
)
if /i "%CHOICE%"=="2" (
    set "MERIDIAN_DISABLE_AUTOPLAY_FLAG=1"
    "%~dp0CyberDeckBrowser.exe"
    set "MERIDIAN_DISABLE_AUTOPLAY_FLAG="
    goto menu
)
if /i "%CHOICE%"=="3" (
    set "MERIDIAN_DISABLE_PROFILE_PERSISTENCE=1"
    "%~dp0CyberDeckBrowser.exe"
    set "MERIDIAN_DISABLE_PROFILE_PERSISTENCE="
    goto menu
)
if /i "%CHOICE%"=="4" (
    set "MERIDIAN_DISABLE_UA_OVERRIDE=1"
    "%~dp0CyberDeckBrowser.exe"
    set "MERIDIAN_DISABLE_UA_OVERRIDE="
    goto menu
)
if /i "%CHOICE%"=="5" (
    set "MERIDIAN_DISABLE_PLUGINS_FLAGS=1"
    "%~dp0CyberDeckBrowser.exe"
    set "MERIDIAN_DISABLE_PLUGINS_FLAGS="
    goto menu
)
if /i "%CHOICE%"=="6" (
    set "MERIDIAN_DISABLE_WIDEVINE_FLAGS=1"
    set "MERIDIAN_DISABLE_AUTOPLAY_FLAG=1"
    set "MERIDIAN_DISABLE_PROFILE_PERSISTENCE=1"
    set "MERIDIAN_DISABLE_UA_OVERRIDE=1"
    set "MERIDIAN_DISABLE_PLUGINS_FLAGS=1"
    "%~dp0CyberDeckBrowser.exe"
    set "MERIDIAN_DISABLE_WIDEVINE_FLAGS="
    set "MERIDIAN_DISABLE_AUTOPLAY_FLAG="
    set "MERIDIAN_DISABLE_PROFILE_PERSISTENCE="
    set "MERIDIAN_DISABLE_UA_OVERRIDE="
    set "MERIDIAN_DISABLE_PLUGINS_FLAGS="
    goto menu
)
if /i "%CHOICE%"=="7" (
    "%~dp0CyberDeckBrowser.exe"
    goto menu
)
if /i "%CHOICE%"=="Q" exit /b 0

goto menu
