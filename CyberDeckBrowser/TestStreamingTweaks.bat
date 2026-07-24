@echo off
setlocal enabledelayedexpansion

REM ============================================================
REM  Test each CyberDeckBrowser streaming/login tweak individually
REM
REM  Run this from wherever CyberDeckBrowser.exe actually lives
REM  (e.g. C:\Program Files\DskoTech\) - it launches the SAME exe
REM  with one env var set at a time so you can bisect which change
REM  is causing a problem (blank pages, Google/reCAPTCHA blocks,
REM  streaming sites not working, slowness). See CyberDeckBrowser/
REM  main.py's _configure_streaming_playback /
REM  _configure_persistent_web_profile docstrings for exactly what
REM  each one does.
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
echo  (or, for 8/9, several) tweak disabled. Close the window when
echo  done testing, then pick the next one. If a specific option
echo  fixes the problem, that tweak (or combination) is the culprit.
echo.
echo  1. Disable Widevine flags         (--widevine-path / --ppapi-widevine-path)
echo  2. Disable autoplay flag          (--autoplay-policy)
echo  3. Disable anti-detection flag    (--disable-blink-features=AutomationControlled)
echo  4. Disable Client Hints flag      (--disable-features=UserAgentClientHint)
echo  5. Disable profile persistence    (org/app name, storage path, cookie policy)
echo  6. Disable User-Agent override
echo  7. Disable plugins/playback flags (PluginsEnabled etc.)
echo  8. Disable ALL SEVEN at once      (should behave like the pre-tweak build)
echo  9. Disable ONLY the fingerprint-related ones (3, 4, 6 - if Google's
echo     "unusual traffic" block is about a mismatched UA/Client Hints/
echo     automation-marker fingerprint rather than DRM/autoplay/persistence,
echo     this isolates that without giving up streaming/login fixes too)
echo  10. Run normally (all tweaks ON, for comparison)
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
    set "MERIDIAN_DISABLE_ANTI_DETECTION_FLAG=1"
    "%~dp0CyberDeckBrowser.exe"
    set "MERIDIAN_DISABLE_ANTI_DETECTION_FLAG="
    goto menu
)
if /i "%CHOICE%"=="4" (
    set "MERIDIAN_DISABLE_CLIENT_HINTS_FLAG=1"
    "%~dp0CyberDeckBrowser.exe"
    set "MERIDIAN_DISABLE_CLIENT_HINTS_FLAG="
    goto menu
)
if /i "%CHOICE%"=="5" (
    set "MERIDIAN_DISABLE_PROFILE_PERSISTENCE=1"
    "%~dp0CyberDeckBrowser.exe"
    set "MERIDIAN_DISABLE_PROFILE_PERSISTENCE="
    goto menu
)
if /i "%CHOICE%"=="6" (
    set "MERIDIAN_DISABLE_UA_OVERRIDE=1"
    "%~dp0CyberDeckBrowser.exe"
    set "MERIDIAN_DISABLE_UA_OVERRIDE="
    goto menu
)
if /i "%CHOICE%"=="7" (
    set "MERIDIAN_DISABLE_PLUGINS_FLAGS=1"
    "%~dp0CyberDeckBrowser.exe"
    set "MERIDIAN_DISABLE_PLUGINS_FLAGS="
    goto menu
)
if /i "%CHOICE%"=="8" (
    set "MERIDIAN_DISABLE_WIDEVINE_FLAGS=1"
    set "MERIDIAN_DISABLE_AUTOPLAY_FLAG=1"
    set "MERIDIAN_DISABLE_ANTI_DETECTION_FLAG=1"
    set "MERIDIAN_DISABLE_CLIENT_HINTS_FLAG=1"
    set "MERIDIAN_DISABLE_PROFILE_PERSISTENCE=1"
    set "MERIDIAN_DISABLE_UA_OVERRIDE=1"
    set "MERIDIAN_DISABLE_PLUGINS_FLAGS=1"
    "%~dp0CyberDeckBrowser.exe"
    set "MERIDIAN_DISABLE_WIDEVINE_FLAGS="
    set "MERIDIAN_DISABLE_AUTOPLAY_FLAG="
    set "MERIDIAN_DISABLE_ANTI_DETECTION_FLAG="
    set "MERIDIAN_DISABLE_CLIENT_HINTS_FLAG="
    set "MERIDIAN_DISABLE_PROFILE_PERSISTENCE="
    set "MERIDIAN_DISABLE_UA_OVERRIDE="
    set "MERIDIAN_DISABLE_PLUGINS_FLAGS="
    goto menu
)
if /i "%CHOICE%"=="9" (
    set "MERIDIAN_DISABLE_ANTI_DETECTION_FLAG=1"
    set "MERIDIAN_DISABLE_CLIENT_HINTS_FLAG=1"
    set "MERIDIAN_DISABLE_UA_OVERRIDE=1"
    "%~dp0CyberDeckBrowser.exe"
    set "MERIDIAN_DISABLE_ANTI_DETECTION_FLAG="
    set "MERIDIAN_DISABLE_CLIENT_HINTS_FLAG="
    set "MERIDIAN_DISABLE_UA_OVERRIDE="
    goto menu
)
if /i "%CHOICE%"=="10" (
    "%~dp0CyberDeckBrowser.exe"
    goto menu
)
if /i "%CHOICE%"=="Q" exit /b 0

goto menu
