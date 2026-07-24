@echo off
setlocal enabledelayedexpansion

REM ============================================================
REM  Meridian Suite - Quick Compile (WITH gameinput_native build)
REM
REM  This is a variant of quickcompile.bat that ADDITIONALLY installs
REM  the Microsoft C++ Build Tools (a multi-GB download, skipped
REM  entirely via vswhere detection if already present) and then builds
REM  and stages gameinput_native.pyd (the real Microsoft GameInput SDK
REM  backend for controller input - see gameinput_native/README.md)
REM  using them. Kept as its own separate file rather than a flag on
REM  the plain quickcompile.bat, same reasoning as
REM  InstallMeridianSuite_WithGameInputBuild.bat /
REM  CompileAndPackage_WithGameInputBuild.bat: most people don't need
REM  it - controller input works fine without it, on the older ctypes
REM  fallback - and the Build Tools are a much bigger download than
REM  everything else this script needs.
REM
REM  Same compile -> stage -> install -> launch pipeline as
REM  InstallMeridianSuite.bat, but WITHOUT any of its dependency
REM  checking/installing steps: no Python presence check/install,
REM  no pip dependency installs, no WebView2/VC++/ffmpeg/SDL3
REM  downloads. Assumes all of that is already in place
REM  (i.e. you've already run InstallMeridianSuite.bat at least
REM  once on this machine) and just rebuilds + reinstalls the
REM  apps themselves as fast as possible - meant for repeat local
REM  rebuilds while iterating, not a first-time/end-user install.
REM
REM  Does, in order:
REM    1. Elevates itself to Administrator if it isn't already
REM       (still needed to write to C:\Program Files\).
REM    2. Compiles all six required apps with their own build
REM       scripts, plus gameinput_native (see above).
REM    3. Stages everything into one flat folder and installs it
REM       to C:\Program Files\DskoTech, same as
REM       InstallMeridianSuite.bat's own staging step.
REM    4. Launches Meridian Launcher from the install folder.
REM
REM  Run from the repo root (the folder containing main.py).
REM  No internet connection needed.
REM ============================================================

REM ---------------------------------------------------------
REM  0. Self-elevate. Writing to C:\Program Files\ needs
REM     Administrator.
REM ---------------------------------------------------------
net session >nul 2>&1
if errorlevel 1 (
    echo Requesting Administrator permission...
    powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
    exit /b
)

set "ROOT=%~dp0"
cd /d "%ROOT%"
set "INSTALL_DIR=C:\Program Files\DskoTech"

echo ============================================================
echo  Meridian Suite - Quick Compile
echo  Source:  %ROOT%
echo  Target:  %INSTALL_DIR%
echo  (No dependency checks - assumes InstallMeridianSuite.bat
echo   has already been run once on this machine.)
echo ============================================================
echo.

REM ---------------------------------------------------------
REM  1. Compile all six required apps using their own build
REM     scripts, exactly like InstallMeridianSuite.bat's own
REM     compile step - just without anything before it.
REM ---------------------------------------------------------
echo [1/3] Compiling all six required apps...
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

REM XInputToKeyboard.exe (Controller Bridge) - best-effort and NOT part of
REM the FAILED check above, same as InstallMeridianSuite.bat.
echo   - XInputToKeyboard ^(optional - only needed for Controller Bridge^)...
pyinstaller "%ROOT%xinput_to_keyboard.spec" --distpath "%ROOT%dist" --workpath "%ROOT%build\xinput_to_keyboard" --noconfirm < NUL
if not exist "%ROOT%dist\XInputToKeyboard.exe" (
    echo     [WARN] Not built - Controller Bridge won't be available in this install.
) else (
    echo     OK - dist\XInputToKeyboard.exe
)
echo.

REM Internal Launcher / Meridian Paint (Apps section plug-ons) - same
REM best-effort treatment as XInputToKeyboard above.
echo   - Internal Launcher ^(optional - Apps section plug-on^)...
pyinstaller "%ROOT%InternalLauncher\InternalLauncher.spec" --distpath "%ROOT%dist" --workpath "%ROOT%build\internal_launcher" --noconfirm < NUL
if not exist "%ROOT%dist\InternalLauncher.exe" (
    echo     [WARN] Not built - the Internal Launcher plug-on won't work in this install.
) else (
    echo     OK - dist\InternalLauncher.exe
)
echo.

echo   - Meridian Paint ^(optional - Apps section plug-on^)...
pyinstaller "%ROOT%MeridianPaint\MeridianPaint.spec" --distpath "%ROOT%dist" --workpath "%ROOT%build\meridian_paint" --noconfirm < NUL
if not exist "%ROOT%dist\MeridianPaint.exe" (
    echo     [WARN] Not built - the Meridian Paint plug-on won't work in this install.
) else (
    echo     OK - dist\MeridianPaint.exe
)
echo.

echo   - Microsoft C++ Build Tools ^(needed to build gameinput_native - this
echo     step alone can take a while on a fresh machine, several GB^)...
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
    set "TEMPDL=%TEMP%\meridian_buildtools_dl"
    mkdir "%TEMPDL%" >nul 2>&1
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
        echo            and re-run this script to try again.
    )
)
echo.

echo   - gameinput_native ^(optional - real GameInput SDK backend^)...
python "%ROOT%gameinput_native\build_and_deploy.py" < NUL
if not exist "%ROOT%gameinput_native\gameinput_native*.pyd" (
    echo     [WARN] Not built - controller input will use the older ctypes
    echo            fallback in this install ^(everything else still works^). If
    echo            the Build Tools step above failed, that's almost always why.
) else (
    echo     OK - built and deployed to all app source folders.
)
echo.

REM ---------------------------------------------------------
REM  2. Stage everything into one flat folder, then install it
REM     to C:\Program Files\DskoTech - identical to
REM     InstallMeridianSuite.bat's own staging step.
REM ---------------------------------------------------------
echo [2/3] Staging and installing to %INSTALL_DIR% ...
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

REM XInputToKeyboard.exe (Controller Bridge) - best-effort, same reasoning
REM as InstallMeridianSuite.bat.
if exist "%ROOT%dist\XInputToKeyboard.exe" (
    copy /y "%ROOT%dist\XInputToKeyboard.exe" "%STAGE%\" >nul
)

REM Internal Launcher / Meridian Paint (Apps section plug-ons) - best-effort.
if exist "%ROOT%dist\InternalLauncher.exe" (
    copy /y "%ROOT%dist\InternalLauncher.exe" "%STAGE%\" >nul
)
if exist "%ROOT%dist\MeridianPaint.exe" (
    copy /y "%ROOT%dist\MeridianPaint.exe" "%STAGE%\" >nul
)

REM gameinput_native.pyd - best-effort, see the build step above. Only
REM ONE copy is needed here (unlike CompileAndPackage.bat's per-app
REM subfolder layout) since this script flattens every app into one
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
copy /y "%ROOT%README.md"            "%STAGE%\" >nul || set "FAILED=1"
copy /y "%ROOT%CONTROLS_README.txt"  "%STAGE%\" >nul || set "FAILED=1"
copy /y "%ROOT%LICENSE.txt"          "%STAGE%\" >nul || set "FAILED=1"
robocopy "%ROOT%Meridian_Exporter" "%STAGE%\Meridian_Exporter" /E /NFL /NDL /NJH /NJS >nul
robocopy "%ROOT%themes" "%STAGE%\themes" /E /NFL /NDL /NJH /NJS >nul
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
REM  3. Launch it.
REM ---------------------------------------------------------
echo [3/3] Launching Meridian Launcher...
start "" "%INSTALL_DIR%\MeridianLauncher.exe"
echo.
echo ============================================================
echo  SUCCESS - rebuilt and reinstalled at:
echo    %INSTALL_DIR%
echo ============================================================
echo.
pause
exit /b 0

:fail
echo.
echo ============================================================
echo  QUICK COMPILE FAILED - see the [ERROR] lines above.
echo ============================================================
pause
exit /b 1
