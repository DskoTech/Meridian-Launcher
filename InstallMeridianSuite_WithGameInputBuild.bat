@echo off
setlocal enabledelayedexpansion

REM ============================================================
REM  Meridian Suite - One-Shot Installer (WITH gameinput_native build)
REM
REM  This is a variant of InstallMeridianSuite.bat that ADDITIONALLY
REM  installs the Microsoft C++ Build Tools (a multi-GB download) and
REM  then builds and stages gameinput_native.pyd (the real Microsoft
REM  GameInput SDK backend for controller input - see
REM  gameinput_native/README.md) using them. Kept as its own separate
REM  file rather than a flag on the main installer since that download
REM  is much larger than everything else the main installer needs, and
REM  most people don't need it - controller input works fine without
REM  it, on the older ctypes fallback. Use this one instead of
REM  InstallMeridianSuite.bat if you specifically want the more
REM  reliable GameInput backend and don't mind the extra download time.
REM
REM  NOTE: gameinput_native/ (an optional compiled C++ extension for
REM  more reliable GameInput controller support - see
REM  gameinput_native/README.md) IS built by this installer, including
REM  the MSVC Build Tools it needs to do so (see the step below) - it
REM  just [WARN]s and everything else still installs and works fine,
REM  falling back to the older ctypes implementation for controller
REM  input - see Settings > Controls' diag readout in any installed app
REM  for DIAG["native_status"] to confirm which one ended up active.
REM
REM  Does everything, in order:
REM    1. Elevates itself to Administrator if it isn't already.
REM    2. Installs Python (3.12 x64, all-users, on PATH) if no
REM       Python is found.
REM    3. Installs every pip dependency all apps need to
REM       build (pywebview, PySide6, pygame, pyinstaller, ...).
REM    4. Compiles all six required apps with their own build
REM       scripts (Meridian Launcher, CyberDeckBrowser, Meridian
REM       Explorer, Meridian FileBrowse + its shell-handler
REM       trampoline, onscreenmenu, Meridian Game Library).
REM    5. Stages the built apps, the Plugins/ and examples/
REM       folders, plus osm.bat, osk.bat, MakeUnmakeShell.ps1,
REM       README.md, CONTROLS_README.txt, and the
REM       Meridian_Exporter Playnite extension into one flat
REM       folder and installs it to C:\Program Files\DskoTech.
REM    6. Downloads and silently installs the runtime
REM       dependencies end users need: the WebView2 Runtime, the
REM       VC++ 2015-2022 x64 Redistributable, ffmpeg (best-effort,
REM       for media thumbnails), and SDL3.dll (best-effort, an
REM       alternate controller input backend - see
REM       gameinput_api.py).
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
    pygame keyboard ^
    pybind11 ^
    pycaw comtypes qrcode
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
echo [3/6] Compiling all seven apps ^(this is the slow part^)...
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

echo   - Meridian FileBrowse ^(+ its default-shell-browser trampoline^)...
pushd "%ROOT%Meridian_FileBrowse"
call "Build_Meridian_FileBrowse.bat" < NUL
popd
if not exist "%ROOT%Meridian_FileBrowse\dist\Meridian FileBrowse.exe" (
    echo     [ERROR] "Meridian FileBrowse.exe" was not produced.
    set "FAILED=1"
)
if not exist "%ROOT%Meridian_FileBrowse\dist\Meridian FileBrowse Shell Handler.exe" (
    echo     [WARN] "Meridian FileBrowse Shell Handler.exe" was not produced -
    echo            the "Make default shell browser" setting won't be offered.
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
echo   OK - all six apps compiled.
echo.

REM XInputToKeyboard.exe (Controller Bridge) is optional and deliberately
REM NOT part of the FAILED check above: if the 'keyboard' package didn't
REM install, or this build fails for any other reason, the rest of the
REM suite still installs and works fine - Controller Bridge just won't
REM be available until it's built successfully some other time.
echo   - XInputToKeyboard ^(optional - only needed for Controller Bridge^)...
pyinstaller "%ROOT%xinput_to_keyboard.spec" --distpath "%ROOT%dist" --workpath "%ROOT%build\xinput_to_keyboard" --noconfirm < NUL
if not exist "%ROOT%dist\XInputToKeyboard.exe" (
    echo     [WARN] Not built - Controller Bridge won't be available in this install.
) else (
    echo     OK - dist\XInputToKeyboard.exe
)
echo.

REM gameinput_native.pyd (optional - real GameInput SDK backend for
REM controller input, see gameinput_native/README.md) is deliberately
REM NOT part of the FAILED check above: this whole step is best-effort,
REM same as XInputToKeyboard above - if any part of it fails, the rest
REM of the suite still installs and works fine on the older ctypes
REM fallback.
REM
REM Building it needs the MSVC Build Tools specifically (pybind11
REM alone, installed above, isn't enough - that's the Python-side
REM binding generator, not a C++ compiler). THIS is the one thing that
REM makes InstallMeridianSuite_WithGameInputBuild.bat a different file
REM from the plain installer rather than a flag on it: the Build Tools
REM are a multi-GB download, so the plain installer deliberately never
REM fetches them. This variant does, right here, the same way it
REM already fetches WebView2/VC++ Redist below - but unlike those two
REM (small, fast Microsoft installers that genuinely no-op in a second
REM or two), vs_buildtools.exe is a heavy bootstrapper that still
REM spends real time re-downloading its own component catalog and
REM doing a "modify" pass even when nothing ends up changing - worth
REM actually detecting "already installed" up front and skipping the
REM whole thing, rather than relying on the bootstrapper's own
REM no-op-if-present behavior the way the smaller installers below do.
echo   - Microsoft C++ Build Tools ^(needed to build gameinput_native^)...
set "VSWHERE=%ProgramFiles(x86)%\Microsoft Visual Studio\Installer\vswhere.exe"
set "VCTOOLS_FOUND="
if exist "%VSWHERE%" (
    for /f "usebackq tokens=*" %%i in (`"%VSWHERE%" -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath 2^>nul`) do (
        if not "%%i"=="" set "VCTOOLS_FOUND=1"
    )
)
if defined VCTOOLS_FOUND (
    echo     OK - already installed, skipping ^(found via vswhere^).
) else (
    echo     Not found - installing ^(this step alone can take a while on a
    echo     fresh machine, several GB^)...
    if exist "%ROOT%Dependencies\vs_buildtools.exe" (
        copy /y "%ROOT%Dependencies\vs_buildtools.exe" "%TEMPDL%\vs_buildtools.exe" >nul
    ) else (
        powershell -NoProfile -Command "[Net.ServicePointManager]::SecurityProtocol='Tls12'; Invoke-WebRequest -Uri 'https://aka.ms/vs/17/release/vs_buildtools.exe' -OutFile '%TEMPDL%\vs_buildtools.exe'"
    )
    if exist "%TEMPDL%\vs_buildtools.exe" (
        "%TEMPDL%\vs_buildtools.exe" --quiet --wait --norestart --nocache ^
            --add Microsoft.VisualStudio.Workload.VCTools --includeRecommended
        echo     OK - installed.
    ) else (
        echo     [WARN] Couldn't download the C++ Build Tools - gameinput_native
        echo            will fail to build below and fall back to the older ctypes
        echo            implementation ^(everything else still works^). Install the
        echo            "Desktop development with C++" workload manually from
        echo            https://visualstudio.microsoft.com/visual-cpp-build-tools/
        echo            and re-run this installer to try again.
    )
)
echo.

echo   - gameinput_native ^(optional - real GameInput SDK backend^)...
%PY% "%ROOT%gameinput_native\build_and_deploy.py" < NUL
if not exist "%ROOT%gameinput_native\gameinput_native*.pyd" (
    echo     [WARN] Not built - controller input will use the older ctypes
    echo            fallback in this install ^(everything else still works^).
    echo            Usually means the C++ Build Tools step above didn't
    echo            complete successfully - see gameinput_native\README.md
    echo            to build it manually, or just re-run this installer.
) else (
    echo     OK - built ^(staged into %%INSTALL_DIR%% below^).
)
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
copy /y "%ROOT%Meridian_FileBrowse\dist\Meridian FileBrowse.exe" "%STAGE%\" >nul || set "FAILED=1"
copy /y "%ROOT%onscreenmenu\dist\onscreenmenu.exe"        "%STAGE%\" >nul || set "FAILED=1"

REM default-shell-browser trampolines - best-effort, not required for the
REM apps themselves to work, only for the "make default" settings
if exist "%ROOT%Meridian_FileBrowse\dist\Meridian FileBrowse Shell Handler.exe" (
    copy /y "%ROOT%Meridian_FileBrowse\dist\Meridian FileBrowse Shell Handler.exe" "%STAGE%\" >nul
)

REM XInputToKeyboard.exe (Controller Bridge) - best-effort, since it's
REM optional. Landing here means it's automatically "next to" Meridian
REM Launcher, which is where main.py looks for it.
if exist "%ROOT%dist\XInputToKeyboard.exe" (
    copy /y "%ROOT%dist\XInputToKeyboard.exe" "%STAGE%\" >nul
)

REM gameinput_native.pyd - best-effort, see the build step above. Only
REM ONE copy is needed here (unlike CompileAndPackage.bat's per-app
REM subfolder layout) since this installer flattens every app into one
REM shared %STAGE%\ folder - every exe that looks for it right next to
REM itself finds this same copy.
for %%F in ("%ROOT%gameinput_native.cp*-win_amd64.pyd") do (
    copy /y "%%F" "%STAGE%\" >nul
)

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
REM Plugins/ (auto-scanned custom sections) and examples/ (the blank
REM plugin template) ride along too, so a fresh install has both the
REM built-in Start plugin and the template ready to go, not just the exes.
robocopy "%ROOT%Plugins" "%STAGE%\Plugins" /E /NFL /NDL /NJH /NJS >nul
robocopy "%ROOT%examples" "%STAGE%\examples" /E /NFL /NDL /NJH /NJS >nul
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

REM SDL3.dll: the "sdl3" input backend option (Settings > Controls in
REM Meridian Launcher/Game Library) needs this sitting right next to the
REM app's exe - see gameinput_api.py's module docstring. It's an
REM alternate backend, not the default (XInput is), so this is
REM best-effort like ffmpeg above: everything still works without it,
REM the sdl3 backend option just won't do anything until it's present.
REM No single stable "always latest" download URL exists for SDL3 the
REM way ffmpeg's gyan.dev mirror does, so this asks GitHub's release API
REM for whatever the latest tagged release's win32-x64 zip actually is.
echo   - SDL3 ^(alternate controller input backend^) - installing into %INSTALL_DIR% ...
if exist "%INSTALL_DIR%\SDL3.dll" (
    echo     OK - SDL3.dll already in the install folder.
) else (
    if exist "%ROOT%Dependencies\SDL3-win64.zip" (
        copy /y "%ROOT%Dependencies\SDL3-win64.zip" "%TEMPDL%\sdl3.zip" >nul
    ) else (
        powershell -NoProfile -Command "[Net.ServicePointManager]::SecurityProtocol='Tls12'; try { $rel = Invoke-RestMethod -Uri 'https://api.github.com/repos/libsdl-org/SDL/releases/latest' -Headers @{ 'User-Agent'='MeridianSuiteInstaller' }; $asset = $rel.assets | Where-Object { $_.name -like '*win32-x64.zip' } | Select-Object -First 1; if ($asset) { Invoke-WebRequest -Uri $asset.browser_download_url -OutFile '%TEMPDL%\sdl3.zip' } } catch {}"
    )
    if exist "%TEMPDL%\sdl3.zip" (
        echo     Extracting SDL3.dll...
        powershell -NoProfile -Command "Expand-Archive -Path '%TEMPDL%\sdl3.zip' -DestinationPath '%TEMPDL%\sdl3' -Force; $dll = Get-ChildItem '%TEMPDL%\sdl3' -Recurse -Filter SDL3.dll | Select-Object -First 1; if ($dll) { Copy-Item $dll.FullName '%INSTALL_DIR%\SDL3.dll' -Force }"
        if exist "%INSTALL_DIR%\SDL3.dll" (
            echo     OK - SDL3.dll installed to %INSTALL_DIR%.
        ) else (
            echo     [WARN] Downloaded but couldn't extract SDL3.dll - the sdl3
            echo            controller backend option will be unavailable until
            echo            it's placed in %INSTALL_DIR% by hand.
        )
    ) else (
        echo     [WARN] Couldn't download SDL3 - the sdl3 controller backend
        echo            option will be unavailable until SDL3.dll is placed in
        echo            %INSTALL_DIR% by hand. ^(Everything else still works;
        echo            XInput, the default backend, doesn't need this.^)
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
