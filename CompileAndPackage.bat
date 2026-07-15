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

echo [1/7] Building Meridian Launcher...
call "%ROOT%buildMeridianLauncher.bat" < NUL
if not exist "%ROOT%dist\MeridianLauncher.exe" (
    echo   [ERROR] Build did not produce dist\MeridianLauncher.exe
    set "FAILED=1"
) else (
    echo   OK - dist\MeridianLauncher.exe
)
echo.

echo [2/7] Building CyberDeckBrowser...
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

echo [3/7] Building Meridian Explorer...
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

echo [4/7] Building Meridian FileBrowse...
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

echo [5/7] Building Meridian NetBrowse...
pushd "%ROOT%Meridian_NetBrowse"
call "buildMeridianNetBrowse.bat" < NUL
popd
if not exist "%ROOT%Meridian_NetBrowse\dist\Meridian NetBrowse\Meridian NetBrowse.exe" (
    echo   [ERROR] Build did not produce "Meridian_NetBrowse\dist\Meridian NetBrowse\Meridian NetBrowse.exe"
    set "FAILED=1"
) else (
    echo   OK - "Meridian_NetBrowse\dist\Meridian NetBrowse\Meridian NetBrowse.exe"
)
echo.

echo [6/7] Building onscreenmenu...
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

echo [7/7] Building Meridian Game Library...
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
echo  All 7 apps compiled. Each app's output is sitting in its
echo  own "dist" folder inside its project folder:
echo    dist\MeridianLauncher.exe
echo    CyberDeckBrowser\dist\CyberDeckBrowser\
echo    Meridian_Explorer\dist\
echo    Meridian_FileBrowse\dist\
echo    Meridian_NetBrowse\dist\Meridian NetBrowse\
echo    onscreenmenu\dist\
echo    "Meridian Game Library\dist\Meridian Game Library\"
echo ============================================================
echo.

echo Staging osm.bat and osk.bat into DskoTech\...
if not exist "%ROOT%DskoTech" mkdir "%ROOT%DskoTech"

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

if defined FAILED (
    pause
    exit /b 1
)

echo   OK - DskoTech\osm.bat and DskoTech\osk.bat staged.
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
echo    - All 7 apps compiled to their own dist\ folders.
echo    - osm.bat and osk.bat staged in DskoTech\.
echo    - DskoTech\ copied to C:\Program Files\DskoTech\.
echo ============================================================
pause
endlocal
