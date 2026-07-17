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
REM  hand would. Then stages osm.bat and osk.bat into DskoTech\,
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

echo ============================================================
echo  All 6 apps compiled. Each app's output is sitting in its
echo  own "dist" folder inside its project folder:
echo    dist\MeridianLauncher.exe
echo    CyberDeckBrowser\dist\CyberDeckBrowser\
echo    Meridian_Explorer\dist\
echo    Meridian_FileBrowse\dist\
echo    onscreenmenu\dist\
echo    "Meridian Game Library\dist\Meridian Game Library\"
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

REM onedir apps - full dist contents flattened in
robocopy "%ROOT%CyberDeckBrowser\dist\CyberDeckBrowser" "%ROOT%DskoTech" /E /NFL /NDL /NJH /NJS >nul
if %ERRORLEVEL% GEQ 8 set "FAILED=1"
robocopy "%ROOT%Meridian Game Library\dist\Meridian Game Library" "%ROOT%DskoTech" /E /NFL /NDL /NJH /NJS >nul
if %ERRORLEVEL% GEQ 8 set "FAILED=1"

copy /y "%ROOT%osm.bat" "%ROOT%DskoTech\osm.bat" >nul
if errorlevel 1 (
    echo   [ERROR] Couldn't copy osm.bat into DskoTech\.
    set "FAILED=1"
)

copy /y "%ROOT%osk.bat" "%ROOT%DskoTech\osk.bat" >nul
if errorlevel 1 (
    echo   [ERROR] Couldn't copy osk.bat into DskoTech\.
    set "FAILED=1"
)

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
echo    - osm.bat and osk.bat staged in DskoTech\.
echo    - DskoTech\ copied to C:\Program Files\DskoTech\.
echo ============================================================
pause
endlocal
