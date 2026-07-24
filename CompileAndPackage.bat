@echo off
setlocal enabledelayedexpansion

REM ============================================================
REM  Meridian Ecosystem - Compile All & Package
REM
REM  Stays in the Meridian-Launcher-main root folder. Builds all
REM  five apps from their own folders (each app's own build
REM  script handles installing its own requirements and running
REM  PyInstaller), leaving each app's compiled output in its own
REM  "dist" folder, exactly like running each build script by
REM  hand would. Then stages the built exes into DskoTech\,
REM  and copies DskoTech\ to C:\Program Files\DskoTech\.
REM
REM  Run this as Administrator - writing to C:\Program Files\
REM  normally requires elevated permission.
REM ============================================================

set "ROOT=%~dp0"
cd /d "%ROOT%"

set "FAILED="

echo ============================================================
echo  Meridian Ecosystem - Compile All ^& Package
echo ============================================================
echo.

echo [1/6] Building Meridian Launcher...
call "%ROOT%buildMeridianLauncher.bat" < NUL
if not exist "%ROOT%dist\MeridianLauncher.exe" (
    echo   [ERROR] Build did not produce dist\MeridianLauncher.exe
    set "FAILED=1"
) else (
    echo   OK - dist\MeridianLauncher.exe
)
echo.

echo [2/6] Building CyberDeckBrowser...
pushd "%ROOT%CyberDeckBrowser"
call "buildCyberDeckBrowser.bat" < NUL
popd
if not exist "%ROOT%CyberDeckBrowser\dist\CyberDeckBrowser\CyberDeckBrowser.exe" (
    echo   [ERROR] Build did not produce CyberDeckBrowser\dist\CyberDeckBrowser\CyberDeckBrowser.exe
    set "FAILED=1"
) else (
    echo   OK - CyberDeckBrowser\dist\CyberDeckBrowser\CyberDeckBrowser.exe
)
echo.

echo [3/6] Building Meridian Explorer...
pushd "%ROOT%Meridian_Explorer"
call "Build_Meridian_Explorer.bat" < NUL
popd
if not exist "%ROOT%Meridian_Explorer\dist\Meridian Explorer.exe" (
    echo   [ERROR] Build did not produce Meridian_Explorer\dist\Meridian Explorer.exe
    set "FAILED=1"
) else (
    echo   OK - Meridian_Explorer\dist\Meridian Explorer.exe
)
echo.

echo [4/6] Building Meridian FileBrowse...
pushd "%ROOT%Meridian_FileBrowse"
call "Build_Meridian_FileBrowse.bat" < NUL
popd
if not exist "%ROOT%Meridian_FileBrowse\dist\Meridian FileBrowse.exe" (
    echo   [ERROR] Build did not produce Meridian_FileBrowse\dist\Meridian FileBrowse.exe
    set "FAILED=1"
) else (
    echo   OK - Meridian_FileBrowse\dist\Meridian FileBrowse.exe
)
echo.

REM Meridian NetBrowse used to build here as its own app - retired and
REM merged back into CyberDeckBrowser (see its main.py: --box=/
REM --minimal-menu). Running two full QtWebEngine/Chromium bundles side
REM by side was the single biggest contributor to the suite's compiled
REM size; CyberDeckBrowser above now covers everything NetBrowse did.

echo [5/6] Building onscreenmenu...
pushd "%ROOT%onscreenmenu"
call "buildonscreenmenu.bat" < NUL
popd
if not exist "%ROOT%onscreenmenu\dist\onscreenmenu.exe" (
    echo   [ERROR] Build did not produce onscreenmenu\dist\onscreenmenu.exe
    set "FAILED=1"
) else (
    echo   OK - onscreenmenu\dist\onscreenmenu.exe
)
echo.

echo [6/6] Building Meridian Game Library...
pushd "%ROOT%Meridian Game Library"
call "build_MeridianGameLibrary.bat" < NUL
popd
if not exist "%ROOT%Meridian Game Library\dist\Meridian Game Library\Meridian Game Library.exe" (
    echo   [ERROR] Build did not produce "Meridian Game Library\dist\Meridian Game Library\Meridian Game Library.exe"
    set "FAILED=1"
) else (
    echo   OK - "Meridian Game Library\dist\Meridian Game Library\Meridian Game Library.exe"
)
echo.

if defined FAILED (
    echo ============================================================
    echo  One or more builds FAILED - see the [ERROR] lines above.
    echo  Packaging step skipped.
    echo ============================================================
    pause
    exit /b 1
)

echo   - XInputToKeyboard (optional - only needed for Controller Bridge)...
pyinstaller "%ROOT%xinput_to_keyboard.spec" --distpath "%ROOT%dist" --workpath "%ROOT%build\xinput_to_keyboard" --noconfirm < NUL
if not exist "%ROOT%dist\XInputToKeyboard.exe" (
    echo     [WARN] Not built - Controller Bridge won't be available in this
    echo     build ^(everything else still works^). Usually means the
    echo     'keyboard' package isn't installed: pip install keyboard
    echo     --break-system-packages and try again.
) else (
    echo     OK - dist\XInputToKeyboard.exe
)
echo.

echo   - Internal Launcher (optional - Apps section plug-on, embeds an
echo     arbitrary picked file/program's window inline)...
pyinstaller "%ROOT%InternalLauncher\InternalLauncher.spec" --distpath "%ROOT%dist" --workpath "%ROOT%build\internal_launcher" --noconfirm < NUL
if not exist "%ROOT%dist\InternalLauncher.exe" (
    echo     [WARN] Not built - the Internal Launcher plug-on won't work in
    echo     this build ^(everything else still works^). Usually means the
    echo     'psutil' package isn't installed.
) else (
    echo     OK - dist\InternalLauncher.exe
)
echo.

echo   - Meridian Paint (optional - Apps section plug-on, simple
echo     controller-friendly paint program)...
pyinstaller "%ROOT%MeridianPaint\MeridianPaint.spec" --distpath "%ROOT%dist" --workpath "%ROOT%build\meridian_paint" --noconfirm < NUL
if not exist "%ROOT%dist\MeridianPaint.exe" (
    echo     [WARN] Not built - the Meridian Paint plug-on won't work in
    echo     this build ^(everything else still works^).
) else (
    echo     OK - dist\MeridianPaint.exe
)
echo.

echo ============================================================
echo  All 6 apps compiled. Each app's output is sitting in its
echo  own "dist" folder inside its project folder:
echo    dist\MeridianLauncher.exe
echo    CyberDeckBrowser\dist\CyberDeckBrowser\
echo    Meridian_Explorer\dist\
echo    Meridian_FileBrowse\dist\
echo    onscreenmenu\dist\
echo    "Meridian Game Library\dist\Meridian Game Library\"
echo  Plus, if the 'keyboard' package was available: dist\XInputToKeyboard.exe
echo ============================================================
echo.

echo Staging all compiled apps, Plugins/examples, and companion files into DskoTech\...
if exist "%ROOT%DskoTech" rmdir /s /q "%ROOT%DskoTech"
mkdir "%ROOT%DskoTech"

REM onefile apps - single exes straight in
copy /y "%ROOT%dist\MeridianLauncher.exe"                    "%ROOT%DskoTech\" >nul || set "FAILED=1"
copy /y "%ROOT%Meridian_Explorer\dist\Meridian Explorer.exe"  "%ROOT%DskoTech\" >nul || set "FAILED=1"
copy /y "%ROOT%Meridian_FileBrowse\dist\Meridian FileBrowse.exe" "%ROOT%DskoTech\" >nul || set "FAILED=1"
copy /y "%ROOT%onscreenmenu\dist\onscreenmenu.exe"            "%ROOT%DskoTech\" >nul || set "FAILED=1"

REM default-shell-browser trampolines - best-effort only
if exist "%ROOT%Meridian_FileBrowse\dist\Meridian FileBrowse Shell Handler.exe" (
    copy /y "%ROOT%Meridian_FileBrowse\dist\Meridian FileBrowse Shell Handler.exe" "%ROOT%DskoTech\" >nul
)

REM XInputToKeyboard.exe (Controller Bridge) - best-effort only, since the
REM 'keyboard' package might not be installed and that's fine, everything
REM else still works without it. main.py looks for it right next to
REM MeridianLauncher.exe.
if exist "%ROOT%dist\XInputToKeyboard.exe" (
    copy /y "%ROOT%dist\XInputToKeyboard.exe" "%ROOT%DskoTech\" >nul
)

REM InternalLauncher.exe (Internal Launcher plug-on) - best-effort only.
REM Lives next to MeridianLauncher.exe, same convention as every other
REM companion exe here - see plugin_manager.get_plugin_exe_path.
if exist "%ROOT%dist\InternalLauncher.exe" (
    copy /y "%ROOT%dist\InternalLauncher.exe" "%ROOT%DskoTech\" >nul
)

REM MeridianPaint.exe (Meridian Paint plug-on) - best-effort only.
if exist "%ROOT%dist\MeridianPaint.exe" (
    copy /y "%ROOT%dist\MeridianPaint.exe" "%ROOT%DskoTech\" >nul
)

REM onedir apps - full dist contents flattened in
robocopy "%ROOT%CyberDeckBrowser\dist\CyberDeckBrowser" "%ROOT%DskoTech" /E /NFL /NDL /NJH /NJS >nul
if %ERRORLEVEL% GEQ 8 set "FAILED=1"
robocopy "%ROOT%Meridian Game Library\dist\Meridian Game Library" "%ROOT%DskoTech" /E /NFL /NDL /NJH /NJS >nul
if %ERRORLEVEL% GEQ 8 set "FAILED=1"

REM osm.bat/osk.bat are no longer needed - onscreenmenu launching and
REM OSK toggling are both fully internalized in Python now (see
REM main.py _launch_onscreenmenu / onscreenmenu toggle_osk), so there is
REM nothing left to stage here.

REM Plugins/ (auto-scanned custom sections), examples/ (blank plugin
REM template), and themes/ ride along too.
robocopy "%ROOT%Plugins" "%ROOT%DskoTech\Plugins" /E /NFL /NDL /NJH /NJS >nul
robocopy "%ROOT%examples" "%ROOT%DskoTech\examples" /E /NFL /NDL /NJH /NJS >nul
robocopy "%ROOT%themes" "%ROOT%DskoTech\themes" /E /NFL /NDL /NJH /NJS >nul

if defined FAILED (
    pause
    exit /b 1
)

echo   OK - DskoTech\ staged with every compiled app plus Plugins/examples/themes.
echo.

echo Copying DskoTech\ to C:\Program Files\DskoTech\ ...
robocopy "%ROOT%DskoTech" "C:\Program Files\DskoTech" /E /NFL /NDL /NJH /NJS >nul
if %ERRORLEVEL% GEQ 8 (
    echo.
    echo ============================================================
    echo  [ERROR] robocopy failed to copy DskoTech\ to
    echo  C:\Program Files\DskoTech\.
    echo  Try running this script as Administrator - Program Files
    echo  normally needs elevated permission to write to.
    echo ============================================================
    pause
    exit /b 1
)

echo.
echo ============================================================
echo  SUCCESS
echo    - All 6 apps compiled to their own dist\ folders.
echo    - onscreenmenu/OSK-toggle launching is internalized in Python
    echo      now, no separate osm.bat/osk.bat staging needed.
echo    - DskoTech\ copied to C:\Program Files\DskoTech\.
echo ============================================================
pause
endlocal
