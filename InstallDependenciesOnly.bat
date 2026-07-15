@echo off
setlocal enabledelayedexpansion

REM ============================================================
REM  Meridian Suite - Runtime Dependencies Installer (only)
REM
REM  Installs just the runtime dependencies end users need to
REM  RUN the already-compiled Meridian Suite - no Python, no
REM  pip, no compiling. Meant for machines where the built
REM  C:\Program Files\DskoTech folder was copied over manually
REM  or is about to be.
REM
REM    - Microsoft Edge WebView2 Runtime   (required: Meridian
REM      Launcher / Game Library windows won't open without it)
REM    - VC++ 2015-2022 x64 Redistributable
REM    - ffmpeg + ffprobe, extracted into C:\Program Files\DskoTech
REM    - Adds C:\Program Files\DskoTech to the system PATH
REM
REM  Uses local copies from a Dependencies\ folder next to this
REM  script when present (see DownloadDependencyInstallers /
REM  MeridianSuite-Dependencies.zip); downloads only what's
REM  missing. Run as Administrator (it self-elevates).
REM ============================================================

net session >nul 2>&1
if errorlevel 1 (
    echo Requesting Administrator permission...
    powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
    exit /b
)

if defined MERIDIAN_ROOT (
    set "ROOT=%MERIDIAN_ROOT%"
) else (
    set "ROOT=%~dp0"
)
if not "%ROOT:~-1%"=="\" set "ROOT=%ROOT%\"
cd /d "%ROOT%"

set "INSTALL_DIR=C:\Program Files\DskoTech"
set "DEPDIR=%ROOT%Dependencies"
set "TEMPDL=%TEMP%\MeridianSuiteSetup"
if not exist "%TEMPDL%" mkdir "%TEMPDL%"
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"

echo ============================================================
echo  Meridian Suite - Runtime Dependencies Installer
echo  Target: %INSTALL_DIR%
if exist "%DEPDIR%" echo  Using local installers from: %DEPDIR%
echo ============================================================
echo.

echo [1/4] Microsoft Edge WebView2 Runtime...
if exist "%DEPDIR%\webview2setup.exe" (
    copy /y "%DEPDIR%\webview2setup.exe" "%TEMPDL%\webview2setup.exe" >nul
) else (
    powershell -NoProfile -Command "[Net.ServicePointManager]::SecurityProtocol='Tls12'; Invoke-WebRequest -Uri 'https://go.microsoft.com/fwlink/p/?LinkId=2124703' -OutFile '%TEMPDL%\webview2setup.exe'"
)
if exist "%TEMPDL%\webview2setup.exe" (
    "%TEMPDL%\webview2setup.exe" /silent /install
    echo   OK
) else (
    echo   [WARN] Couldn't get WebView2 - if Meridian Launcher's window
    echo          doesn't open, install it manually from
    echo          https://developer.microsoft.com/microsoft-edge/webview2/
)
echo.

echo [2/4] Visual C++ 2015-2022 Redistributable ^(x64^)...
if exist "%DEPDIR%\vc_redist.x64.exe" (
    copy /y "%DEPDIR%\vc_redist.x64.exe" "%TEMPDL%\vc_redist.x64.exe" >nul
) else (
    powershell -NoProfile -Command "[Net.ServicePointManager]::SecurityProtocol='Tls12'; Invoke-WebRequest -Uri 'https://aka.ms/vs/17/release/vc_redist.x64.exe' -OutFile '%TEMPDL%\vc_redist.x64.exe'"
)
if exist "%TEMPDL%\vc_redist.x64.exe" (
    "%TEMPDL%\vc_redist.x64.exe" /install /quiet /norestart
    echo   OK
) else (
    echo   [WARN] Couldn't get the VC++ redistributable - it's usually
    echo          already installed, so this is likely fine.
)
echo.

echo [3/4] ffmpeg - installing into %INSTALL_DIR% ...
if exist "%INSTALL_DIR%\ffmpeg.exe" (
    echo   OK - ffmpeg.exe already in the install folder.
) else (
    if exist "%DEPDIR%\ffmpeg-win64.zip" (
        copy /y "%DEPDIR%\ffmpeg-win64.zip" "%TEMPDL%\ffmpeg.zip" >nul
    ) else (
        powershell -NoProfile -Command "[Net.ServicePointManager]::SecurityProtocol='Tls12'; Invoke-WebRequest -Uri 'https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip' -OutFile '%TEMPDL%\ffmpeg.zip'"
    )
    if exist "%TEMPDL%\ffmpeg.zip" (
        echo   Extracting ffmpeg.exe and ffprobe.exe...
        powershell -NoProfile -Command "Expand-Archive -Path '%TEMPDL%\ffmpeg.zip' -DestinationPath '%TEMPDL%\ffmpeg' -Force; $bin = Get-ChildItem '%TEMPDL%\ffmpeg' -Recurse -Filter ffmpeg.exe | Select-Object -First 1; if ($bin) { Copy-Item $bin.FullName '%INSTALL_DIR%\ffmpeg.exe' -Force; Copy-Item (Join-Path $bin.DirectoryName 'ffprobe.exe') '%INSTALL_DIR%\ffprobe.exe' -Force }"
        if exist "%INSTALL_DIR%\ffmpeg.exe" (
            echo   OK - ffmpeg.exe and ffprobe.exe installed to %INSTALL_DIR%.
        ) else (
            echo   [WARN] Couldn't extract ffmpeg - media thumbnails will be
            echo          disabled until ffmpeg is on PATH.
        )
    ) else (
        echo   [WARN] Couldn't get ffmpeg - media thumbnails will be disabled
        echo          until ffmpeg is on PATH. Everything else still works.
    )
)
echo.

echo [4/4] Adding %INSTALL_DIR% to the system PATH ^(if needed^)...
powershell -NoProfile -Command "$p=[Environment]::GetEnvironmentVariable('Path','Machine'); if ($p -notlike '*%INSTALL_DIR%*') { [Environment]::SetEnvironmentVariable('Path', $p.TrimEnd(';') + ';%INSTALL_DIR%', 'Machine'); Write-Host '  OK - added (takes effect in new programs/consoles).' } else { Write-Host '  OK - already on PATH.' }"
echo.

echo ============================================================
echo  DONE - runtime dependencies are installed. If the DskoTech
echo  apps are already in %INSTALL_DIR%, they're ready to run.
echo ============================================================
pause
exit /b 0
