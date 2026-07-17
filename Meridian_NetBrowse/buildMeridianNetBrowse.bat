@echo off
setlocal

REM ================================================
REM Meridian NetBrowse Build Script
REM
REM Compiles the project into a standalone Windows
REM executable using PyInstaller.
REM
REM Output: dist\Meridian NetBrowse.exe (single file)
REM ================================================

cd /d "%~dp0"

echo.
echo === Installing/upgrading build tools ===
python -m pip install --upgrade pyinstaller pyinstaller-hooks-contrib
if errorlevel 1 (
    echo.
    echo Failed to install PyInstaller. Make sure Python
    echo and pip are installed and available on PATH.
    pause
    exit /b 1
)

echo.
echo === Installing app dependencies ===
python -m pip install -r Requirements.txt
if errorlevel 1 (
    echo.
    echo Failed to install dependencies from Requirements.txt.
    pause
    exit /b 1
)

echo.
echo === Cleaning previous build ===
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist "Meridian NetBrowse.spec" del /q "Meridian NetBrowse.spec"

echo.
echo === Building Meridian NetBrowse.exe ===
REM --onefile: a single .exe, no loose files/folder structure sitting next
REM to it exposing the app's internals - per explicit request, trading off
REM against a known real risk: QtWebEngine's helper process and resource
REM files normally want to sit on disk next to the exe, and --onefile's
REM temp-extraction-on-launch model has been unreliable for that with some
REM PySide6/QtWebEngine version combos (symptoms: blank/white browser view,
REM or a visible extraction delay every launch). If you hit either of
REM those after building this way, switch back to --onedir (see git
REM history / earlier revision of this script) - that's the safe fallback,
REM just with a visible internals folder instead of one file.
REM
REM --collect-all PySide6 / shiboken6: PySide6's own DLL-directory setup
REM code needs shiboken6's binaries fully present at a specific relative
REM location. The default PyInstaller hooks don't always grab all of it,
REM which causes an ImportError like "...shiboken6\libshiboken does not
REM exist" at startup. Collecting everything from both packages explicitly
REM avoids that.
REM
REM --windowed hides the console window - Meridian Launcher runs this
REM boxed inside its own UI, so a separate visible console behind/around
REM it looks like a bug, not a terminal a person is meant to read.

REM NOTE: --collect-all PySide6 (blanket) pulls in QtQuick/QtQml/Qt Labs
REM Platform too, even though this app only uses QtWidgets/QtGui/QtCore/
REM QtWebEngine*. That unused QML machinery is what was causing the build
REM to fail looking for qrc_qmake_qtlabs_assetdownloader_init.cpp.obj -
REM PyInstaller's PySide6 hook tries to rcc-compile Qt Labs Platform's
REM AssetDownloader resource, and that step breaks in a lot of PySide6 +
REM PyInstaller version combinations. Collecting only what's actually
REM imported avoids that build step entirely. --clean also purges
REM PyInstaller's own cache, since a stale one can reproduce this same
REM error even after switching to targeted collects.
pyinstaller --noconfirm --clean --onefile --windowed --name "Meridian NetBrowse" ^
    --icon "icon.ico" ^
    --collect-all PySide6.QtWidgets ^
    --collect-all PySide6.QtGui ^
    --collect-all PySide6.QtCore ^
    --collect-all PySide6.QtWebEngineWidgets ^
    --collect-all PySide6.QtWebEngineCore ^
    --collect-all PySide6.QtNetwork ^
    --collect-all shiboken6 ^
    --exclude-module PySide6.QtQml ^
    --exclude-module PySide6.QtQuick ^
    --exclude-module PySide6.QtQuickWidgets ^
    --exclude-module PySide6.QtQuick3D ^
    --exclude-module PySide6.QtQuickControls2 ^
    --exclude-module PySide6.QtMultimedia ^
    --exclude-module PySide6.QtMultimediaWidgets ^
    --exclude-module PySide6.QtPdf ^
    --exclude-module PySide6.QtPdfWidgets ^
    --exclude-module PySide6.QtBluetooth ^
    --exclude-module PySide6.QtNfc ^
    --exclude-module PySide6.QtPositioning ^
    --exclude-module PySide6.QtSensors ^
    --exclude-module PySide6.QtSerialPort ^
    --exclude-module PySide6.QtSql ^
    --exclude-module PySide6.QtTest ^
    --exclude-module PySide6.QtDesigner ^
    --exclude-module PySide6.QtHelp ^
    --exclude-module PySide6.Qt3DCore ^
    --exclude-module PySide6.Qt3DRender ^
    --exclude-module PySide6.QtCharts ^
    --exclude-module PySide6.QtDataVisualization ^
    --exclude-module PySide6.QtRemoteObjects ^
    --exclude-module PySide6.QtScxml ^
    --exclude-module PySide6.QtStateMachine ^
    --exclude-module PySide6.QtTextToSpeech ^
    launcher.py

if errorlevel 1 (
    echo.
    echo Build failed - see the PyInstaller output above.
    pause
    exit /b 1
)

echo.
echo Building the "default system web browser" trampoline...
pyinstaller --noconfirm --onefile --windowed --distpath . --workpath build_trampoline ^
    --name "Meridian NetBrowse Shell Handler" ^
    netbrowse_shell_handler.py

if errorlevel 1 (
    echo.
    echo ============================================================
    echo  Trampoline build FAILED - Meridian NetBrowse.exe itself is
    echo  still fine; the "Make default system web browser" macro just
    echo  won't be offered until this is built too.
    echo ============================================================
    pause
    exit /b 1
)

REM osk.bat/icon.ico now sit next to the single .exe as real sibling files
REM (not bundled --add-data, since --onefile extracts those to a temp
REM folder at runtime rather than the exe's real folder - code that looks
REM for "osk.bat next to me" needs it to actually be there on disk).
copy /y "osk.bat" "dist\osk.bat" >nul
copy /y "icon.ico" "dist\icon.ico" >nul

echo.
echo ================================================
echo Build complete.
echo.
echo Your executables are at:
echo   dist\Meridian NetBrowse.exe   (a single file - no exposed source/
echo     internals folder, nothing else needed to run it)
echo   Meridian NetBrowse Shell Handler.exe  (only needed for the
echo     "Make Meridian NetBrowse the default system web browser" setting)
echo.
echo Copy dist\Meridian NetBrowse.exe, dist\osk.bat, and dist\icon.ico
echo together to wherever Meridian Launcher.exe lives.
echo ================================================
pause
