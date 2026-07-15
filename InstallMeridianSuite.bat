@echo off
setlocal enabledelayedexpansion

REM ============================================================
REM  Meridian Suite - One-Shot Installer
REM
REM  Does everything, in order:
REM    1. Elevates itself to Administrator if it isn't already.
REM    2. Installs Python (3.12 x64, all-users, on PATH) if no
REM       Python is found.
REM    3. Installs every pip dependency all five apps need to
REM       build (pywebview, PySide6, pygame, pyinstaller, ...).
REM    4. Compiles all five apps with their own build scripts.
REM    5. Stages the built apps plus osm.bat, osk.bat,
REM       MakeUnmakeShell.ps1, README.md, CONTROLS_README.txt,
REM       and the Meridian_Exporter Playnite extension into one
REM       flat folder and installs it to C:\Program Files\DskoTech.
REM    6. Downloads and silently installs the runtime
REM       dependencies end users need: the WebView2 Runtime and
REM       the VC++ 2015-2022 x64 Redistributable (plus ffmpeg
REM       via winget, best-effort, for media thumbnails).
REM    7. Launches Meridian Launcher from the install folder.
REM
REM  Run from the repo root (the folder containing main.py).
REM  Needs an internet connection for steps 2 and 6.
REM ============================================================

REM ---------------------------------------------------------
REM  0. Self-elevate. Writing to C:\Program Files\ and running
REM     the redist installers both need Administrator.
REM ---------------------------------------------------------
net session >nul 2>&1
if errorlevel 1 (
    echo Requesting Administrator permission...
    powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
    exit /b
)

REM When run via the InstallMeridianSuite.exe wrapper, the batch file
REM itself lives in %TEMP%, so the wrapper passes the real repo folder
REM in MERIDIAN_ROOT. Running the .bat directly still works as before.
if defined MERIDIAN_ROOT (
    set "ROOT=%MERIDIAN_ROOT%"
) else (
    set "ROOT=%~dp0"
)
if not "%ROOT:~-1%"=="\" set "ROOT=%ROOT%\"
cd /d "%ROOT%"
set "INSTALL_DIR=C:\Program Files\DskoTech"
set "TEMPDL=%TEMP%\MeridianSuiteSetup"
if not exist "%TEMPDL%" mkdir "%TEMPDL%"

echo ============================================================
echo  Meridian Suite - One-Shot Installer
echo  Source:  %ROOT%
echo  Target:  %INSTALL_DIR%
echo ============================================================
echo.

REM ---------------------------------------------------------
REM  1. Python: find it, or download and install it.
REM ---------------------------------------------------------
echo [1/6] Checking for Python...
set "PY="
where python >nul 2>&1 && set "PY=python"
if not defined PY (
    where py >nul 2>&1 && set "PY=py -3"
)
if defined PY (
    %PY% --version
    echo   OK - Python already installed.
) else (
    if exist "%ROOT%Dependencies\python-installer.exe" (
        echo   Python not found. Using bundled Dependencies\python-installer.exe...
        copy /y "%ROOT%Dependencies\python-installer.exe" "%TEMPDL%\python-installer.exe" >nul
    ) else (
        echo   Python not found. Downloading Python 3.12 ^(x64^)...
        set "PYURL=https://www.python.org/ftp/python/3.12.8/python-3.12.8-amd64.exe"
        powershell -NoProfile -Command "[Net.ServicePointManager]::SecurityProtocol='Tls12'; Invoke-WebRequest -Uri '!PYURL!' -OutFile '%TEMPDL%\python-installer.exe'"
    )
    if not exist "%TEMPDL%\python-installer.exe" (
        echo   [ERROR] Couldn't download the Python installer. Check your
        echo           internet connection and re-run this script.
        goto :fail
    )
    echo   Installing Python silently ^(all users, added to PATH^)...
    "%TEMPDL%\python-installer.exe" /quiet InstallAllUsers=1 PrependPath=1 Include_launcher=1 Include_test=0
    if errorlevel 1 (
        echo   [ERROR] The Python installer reported a failure.
        goto :fail
    )
    REM The current shell doesn't see the new PATH; use the known
    REM all-users install location directly for the rest of this run.
    set "PY=C:\Program Files\Python312\python.exe"
    if not exist "!PY!" (
        echo   [ERROR] Python installed but wasn't found at !PY!.
        echo           Close this window and re-run the script - the fresh
        echo           PATH will be picked up in a new console.
        goto :fail
    )
    echo   OK - Python installed.
)
echo.

REM ---------------------------------------------------------
REM  2. pip dependencies for every app (build-time). Each
REM     app's build script also installs its own, but doing it
REM     all up front means one early, clear failure point
REM     instead of five late ones.
REM ---------------------------------------------------------
echo [2/6] Installing Python build dependencies...
%PY% -m pip install --upgrade pip
%PY% -m pip install --upgrade ^
    pyinstaller ^
    pywebview mutagen Pillow psutil pywin32 ^
    PySide6 shiboken6 ^
    pygame keyboard
if errorlevel 1 (
    echo   [ERROR] pip failed to install one or more packages - scroll up
    echo           for the actual error.
    goto :fail
)
REM pywin32 post-install (registers the COM helpers it needs) -
REM harmless if it's already been done.
%PY% -m pywin32_postinstall -install >nul 2>&1
echo   OK - all Python packages installed.
echo.

REM ---------------------------------------------------------
REM  3. Compile all five apps using their own build scripts,
REM     exactly like CompileAndPackage.bat does.
REM ---------------------------------------------------------
echo [3/6] Compiling all five apps ^(this is the slow part^)...
set "FAILED="

echo   - Meridian Launcher...
call "%ROOT%buildMeridianLauncher.bat" < NUL
if not exist "%ROOT%dist\MeridianLauncher.exe" (
    echo     [ERROR] dist\MeridianLauncher.exe was not produced.
    set "FAILED=1"
)

echo   - CyberDeckBrowser...
pushd "%ROOT%CyberDeckBrowser"
call "buildCyberDeckBrowser.bat" < NUL
popd
if not exist "%ROOT%CyberDeckBrowser\dist\CyberDeckBrowser\CyberDeckBrowser.exe" (
    echo     [ERROR] CyberDeckBrowser.exe was not produced.
    set "FAILED=1"
)

echo   - Meridian Explorer...
pushd "%ROOT%Meridian_Explorer"
call "Build_Meridian_Explorer.bat" < NUL
popd
if not exist "%ROOT%Meridian_Explorer\dist\Meridian Explorer.exe" (
    echo     [ERROR] "Meridian Explorer.exe" was not produced.
    set "FAILED=1"
)

echo   - onscreenmenu...
pushd "%ROOT%onscreenmenu"
call "buildonscreenmenu.bat" < NUL
popd
if not exist "%ROOT%onscreenmenu\dist\onscreenmenu.exe" (
    echo     [ERROR] onscreenmenu.exe was not produced.
    set "FAILED=1"
)

echo   - Meridian Game Library...
pushd "%ROOT%Meridian Game Library"
call "build_MeridianGameLibrary.bat" < NUL
popd
if not exist "%ROOT%Meridian Game Library\dist\Meridian Game Library\Meridian Game Library.exe" (
    echo     [ERROR] "Meridian Game Library.exe" was not produced.
    set "FAILED=1"
)

if defined FAILED (
    echo.
    echo   One or more builds FAILED - see the [ERROR] lines above.
    echo   Nothing has been installed.
    goto :fail
)
echo   OK - all five apps compiled.
echo.

REM ---------------------------------------------------------
REM  4. Stage everything into one flat folder, then install it
REM     to C:\Program Files\DskoTech. The two --onedir apps use
REM     uniquely named contents directories
REM     (CyberDeckBrowser_internal / MeridianGameLibrary_internal,
REM     set in their build scripts) so flattening them together
REM     is collision-free, and Meridian Launcher finds every
REM     sibling exe right next to itself like it expects.
REM ---------------------------------------------------------
echo [4/6] Staging and installing to %INSTALL_DIR% ...
set "STAGE=%ROOT%DskoTech"
if exist "%STAGE%" rmdir /s /q "%STAGE%"
mkdir "%STAGE%"

REM onefile apps - single exes straight in
copy /y "%ROOT%dist\MeridianLauncher.exe"                 "%STAGE%\" >nul || set "FAILED=1"
copy /y "%ROOT%Meridian_Explorer\dist\Meridian Explorer.exe" "%STAGE%\" >nul || set "FAILED=1"
copy /y "%ROOT%onscreenmenu\dist\onscreenmenu.exe"        "%STAGE%\" >nul || set "FAILED=1"

REM onedir apps - full dist contents flattened in
robocopy "%ROOT%CyberDeckBrowser\dist\CyberDeckBrowser" "%STAGE%" /E /NFL /NDL /NJH /NJS >nul
if %ERRORLEVEL% GEQ 8 set "FAILED=1"
robocopy "%ROOT%Meridian Game Library\dist\Meridian Game Library" "%STAGE%" /E /NFL /NDL /NJH /NJS >nul
if %ERRORLEVEL% GEQ 8 set "FAILED=1"

REM companion scripts, docs, and the Playnite exporter extension
copy /y "%ROOT%osm.bat"              "%STAGE%\" >nul || set "FAILED=1"
copy /y "%ROOT%osk.bat"              "%STAGE%\" >nul || set "FAILED=1"
copy /y "%ROOT%MakeUnmakeShell.ps1"  "%STAGE%\" >nul || set "FAILED=1"
copy /y "%ROOT%MeridianExplorerShellIntegration.bat" "%STAGE%\" >nul || set "FAILED=1"
copy /y "%ROOT%README.md"            "%STAGE%\" >nul || set "FAILED=1"
copy /y "%ROOT%CONTROLS_README.txt"  "%STAGE%\" >nul || set "FAILED=1"
robocopy "%ROOT%Meridian_Exporter" "%STAGE%\Meridian_Exporter" /E /NFL /NDL /NJH /NJS >nul
robocopy "%ROOT%themes" "%STAGE%\themes" /E /NFL /NDL /NJH /NJS >nul
copy /y "%ROOT%ImportMeridianexporter.bat" "%STAGE%\" >nul
if %ERRORLEVEL% GEQ 8 set "FAILED=1"

if defined FAILED (
    echo   [ERROR] Staging failed - one of the copies above didn't succeed.
    goto :fail
)

robocopy "%STAGE%" "%INSTALL_DIR%" /E /NFL /NDL /NJH /NJS >nul
if %ERRORLEVEL% GEQ 8 (
    echo   [ERROR] Couldn't copy into %INSTALL_DIR%.
    goto :fail
)
echo   OK - installed to %INSTALL_DIR%.
echo.

REM ---------------------------------------------------------
REM  5. Runtime dependencies for end users:
REM     - WebView2 Runtime (required by Meridian Launcher and
REM       Meridian Game Library; their windows won't open
REM       without it)
REM     - VC++ 2015-2022 x64 Redistributable
REM     - ffmpeg (optional, via winget - enables video/music
REM       thumbnails; everything still runs without it)
REM     Both Microsoft installers no-op quickly when the
REM     runtime is already present, so it's safe to always run.
REM ---------------------------------------------------------
echo [5/6] Installing runtime dependencies...

echo   - Microsoft Edge WebView2 Runtime...
if exist "%ROOT%Dependencies\webview2setup.exe" (
    copy /y "%ROOT%Dependencies\webview2setup.exe" "%TEMPDL%\webview2setup.exe" >nul
) else (
    powershell -NoProfile -Command "[Net.ServicePointManager]::SecurityProtocol='Tls12'; Invoke-WebRequest -Uri 'https://go.microsoft.com/fwlink/p/?LinkId=2124703' -OutFile '%TEMPDL%\webview2setup.exe'"
)
if exist "%TEMPDL%\webview2setup.exe" (
    "%TEMPDL%\webview2setup.exe" /silent /install
    echo     OK
) else (
    echo     [WARN] Couldn't download WebView2 - if Meridian Launcher's
    echo            window doesn't open, install it manually from
    echo            https://developer.microsoft.com/microsoft-edge/webview2/
)

echo   - Visual C++ 2015-2022 Redistributable ^(x64^)...
if exist "%ROOT%Dependencies\vc_redist.x64.exe" (
    copy /y "%ROOT%Dependencies\vc_redist.x64.exe" "%TEMPDL%\vc_redist.x64.exe" >nul
) else (
    powershell -NoProfile -Command "[Net.ServicePointManager]::SecurityProtocol='Tls12'; Invoke-WebRequest -Uri 'https://aka.ms/vs/17/release/vc_redist.x64.exe' -OutFile '%TEMPDL%\vc_redist.x64.exe'"
)
if exist "%TEMPDL%\vc_redist.x64.exe" (
    "%TEMPDL%\vc_redist.x64.exe" /install /quiet /norestart
    echo     OK
) else (
    echo     [WARN] Couldn't download the VC++ redistributable - it's
    echo            usually already installed, so this is likely fine.
)

echo   - ffmpeg ^(for media thumbnails^) - installing into %INSTALL_DIR% ...
if exist "%INSTALL_DIR%\ffmpeg.exe" (
    echo     OK - ffmpeg.exe already in the install folder.
) else (
    if exist "%ROOT%Dependencies\ffmpeg-win64.zip" (
        copy /y "%ROOT%Dependencies\ffmpeg-win64.zip" "%TEMPDL%\ffmpeg.zip" >nul
    ) else (
        powershell -NoProfile -Command "[Net.ServicePointManager]::SecurityProtocol='Tls12'; Invoke-WebRequest -Uri 'https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip' -OutFile '%TEMPDL%\ffmpeg.zip'"
    )
    if exist "%TEMPDL%\ffmpeg.zip" (
        echo     Extracting ffmpeg.exe and ffprobe.exe...
        powershell -NoProfile -Command "Expand-Archive -Path '%TEMPDL%\ffmpeg.zip' -DestinationPath '%TEMPDL%\ffmpeg' -Force; $bin = Get-ChildItem '%TEMPDL%\ffmpeg' -Recurse -Filter ffmpeg.exe | Select-Object -First 1; if ($bin) { Copy-Item $bin.FullName '%INSTALL_DIR%\ffmpeg.exe' -Force; Copy-Item (Join-Path $bin.DirectoryName 'ffprobe.exe') '%INSTALL_DIR%\ffprobe.exe' -Force }"
        if exist "%INSTALL_DIR%\ffmpeg.exe" (
            echo     OK - ffmpeg.exe and ffprobe.exe installed to %INSTALL_DIR%.
        ) else (
            echo     [WARN] Downloaded but couldn't extract ffmpeg - media
            echo            thumbnails will be disabled until ffmpeg is on PATH.
        )
    ) else (
        echo     [WARN] Couldn't download ffmpeg - media thumbnails will be
        echo            disabled until ffmpeg is on PATH. ^(Everything else
        echo            still works.^)
    )
)

REM Put the install folder on the SYSTEM PATH ^(if it isn't already^) so
REM the apps' shutil.which^("ffmpeg"^) finds the copy that now lives next
REM to them, and so osm.bat / osk.bat resolve from anywhere too.
echo   - Adding %INSTALL_DIR% to the system PATH ^(if needed^)...
powershell -NoProfile -Command "$p=[Environment]::GetEnvironmentVariable('Path','Machine'); if ($p -notlike '*%INSTALL_DIR%*') { [Environment]::SetEnvironmentVariable('Path', $p.TrimEnd(';') + ';%INSTALL_DIR%', 'Machine'); Write-Host '    OK - added (takes effect in new programs/consoles).' } else { Write-Host '    OK - already on PATH.' }"
echo.

REM ---------------------------------------------------------
REM  6. Launch it.
REM ---------------------------------------------------------
REM Install the MeridianExporter Playnite extension (the updated one that
REM also exports custom Playnite filter sections) by running its own
REM install script from the install folder, so the Game Library can sync.
echo   - Installing the MeridianExporter Playnite extension...
if exist "%INSTALL_DIR%\ImportMeridianexporter.bat" (
    pushd "%INSTALL_DIR%"
    call "ImportMeridianexporter.bat" < NUL
    popd
    echo     OK ^(copied to %%AppData%%\Playnite\Extensions^).
) else (
    echo     [SKIP] ImportMeridianexporter.bat not found in the install folder.
)
echo.
echo [6/6] Launching Meridian Launcher...
start "" "%INSTALL_DIR%\MeridianLauncher.exe"
echo.
echo ============================================================
echo  SUCCESS - the Meridian Suite is installed at:
echo    %INSTALL_DIR%
echo.
echo  Reminder: for the Game Library, install Playnite and load
echo  the MeridianExporter extension from:
echo    %INSTALL_DIR%\Meridian_Exporter
echo  ^(see README.md / ImportMeridianexporter.bat^)
echo ============================================================
echo.
pause
exit /b 0

:fail
echo.
echo ============================================================
echo  INSTALL FAILED - see the [ERROR] lines above.
echo ============================================================
pause
exit /b 1
