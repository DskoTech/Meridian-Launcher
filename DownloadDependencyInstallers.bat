@echo off
setlocal enabledelayedexpansion

REM ============================================================
REM  Meridian Suite - Dependency Installers Bundler
REM
REM  Downloads every third-party installer the Meridian Suite
REM  needs into Dependencies\ next to this script, then
REM  zips the folder to Dependencies.zip:
REM
REM    python-installer.exe   Python 3.12 (x64)      ~26 MB
REM    webview2setup.exe      WebView2 Evergreen      ~2 MB
REM    vc_redist.x64.exe      VC++ 2015-2022 (x64)   ~25 MB
REM    ffmpeg-win64.zip       ffmpeg release build   ~90 MB
REM
REM  InstallMeridianSuite.bat / .exe automatically uses these
REM  local copies when a Dependencies\ folder sits next
REM  to the repo, instead of downloading - so this zip is all
REM  you need for offline installs. No admin rights needed to
REM  run THIS script; it only downloads and zips.
REM ============================================================

REM When run via the DownloadDependencyInstallers.exe wrapper, the batch
REM file itself lives in %TEMP%, so the wrapper passes the real folder in
REM MERIDIAN_ROOT. Running the .bat directly still works as before.
if defined MERIDIAN_ROOT (
    set "ROOT=%MERIDIAN_ROOT%"
) else (
    set "ROOT=%~dp0"
)
if not "%ROOT:~-1%"=="\" set "ROOT=%ROOT%\"
cd /d "%ROOT%"
set "DEPDIR=%ROOT%Dependencies"
if not exist "%DEPDIR%" mkdir "%DEPDIR%"

set "FAILED="

echo ============================================================
echo  Meridian Suite - downloading dependency installers
echo  into: %DEPDIR%
echo ============================================================
echo.

call :fetch "Python 3.12 (x64)" ^
    "https://www.python.org/ftp/python/3.12.8/python-3.12.8-amd64.exe" ^
    "python-installer.exe"

call :fetch "WebView2 Runtime (Evergreen bootstrapper)" ^
    "https://go.microsoft.com/fwlink/p/?LinkId=2124703" ^
    "webview2setup.exe"

call :fetch "VC++ 2015-2022 Redistributable (x64)" ^
    "https://aka.ms/vs/17/release/vc_redist.x64.exe" ^
    "vc_redist.x64.exe"

call :fetch "ffmpeg (release essentials)" ^
    "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip" ^
    "ffmpeg-win64.zip"

if defined FAILED (
    echo.
    echo ============================================================
    echo  One or more downloads FAILED - see above. The zip was NOT
    echo  created so a partial bundle can't masquerade as a full one.
    echo  Fix your connection and re-run; finished files are kept, so
    echo  only the missing ones will re-download.
    echo ============================================================
    pause
    exit /b 1
)

echo.
echo Zipping to Dependencies.zip ...
if exist "%ROOT%Dependencies.zip" del /q "%ROOT%Dependencies.zip"
powershell -NoProfile -Command "Compress-Archive -Path '%DEPDIR%\*' -DestinationPath '%ROOT%Dependencies.zip' -Force"
if not exist "%ROOT%Dependencies.zip" (
    echo [ERROR] Compress-Archive failed.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo  DONE
echo    Dependencies\        - the loose installers
echo    Dependencies.zip     - the same, zipped
echo.
echo  For an offline install: put the Dependencies
echo  folder (unzipped) next to InstallMeridianSuite.bat/.exe in
echo  the repo root - the installer will use these local copies
echo  automatically instead of downloading.
echo ============================================================
pause
exit /b 0

REM ---- :fetch <label> <url> <filename> ------------------------
:fetch
set "LABEL=%~1"
set "URL=%~2"
set "OUT=%DEPDIR%\%~3"
if exist "%OUT%" (
    echo   [SKIP] %LABEL% - already downloaded.
    goto :eof
)
echo   Downloading %LABEL% ...
powershell -NoProfile -Command "[Net.ServicePointManager]::SecurityProtocol='Tls12'; Invoke-WebRequest -Uri '%URL%' -OutFile '%OUT%'"
if not exist "%OUT%" (
    echo   [ERROR] %LABEL% failed to download.
    set "FAILED=1"
) else (
    echo   OK
)
goto :eof
