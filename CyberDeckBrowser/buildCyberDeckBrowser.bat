@echo off
setlocal

REM ================================================
REM CyberDeckBrowser Build Script
REM
REM Compiles the project into a standalone Windows
REM executable using PyInstaller.
REM
REM Output: dist\CyberDeckBrowser\CyberDeckBrowser.exe
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
if exist CyberDeckBrowser.spec del /q CyberDeckBrowser.spec

echo.
echo === Building CyberDeckBrowser.exe ===
REM --onedir is used (not --onefile) because
REM QtWebEngine needs its helper process and
REM resource files sitting on disk next to the exe -
REM --onefile's temp-extraction model is unreliable
REM for it.
REM
REM --collect-all PySide6 (blanket) pulls in QtQuick/QtQml/Qt Labs
REM Platform, QtMultimedia, QtPdf, and a long tail of other Qt modules
REM this app never imports - each one adds tens to low-hundreds of MB,
REM and with two QtWebEngine-based apps in this suite (this one and
REM Meridian NetBrowse) that duplication was the single biggest
REM contributor to the compiled suite's size. Collecting only the
REM specific modules actually imported (QtWidgets/QtGui/QtCore/
REM QtWebEngine*/QtNetwork) and explicitly excluding the unused Quick/
REM QML/Multimedia/Pdf stacks cuts this down substantially with no
REM functional change - same fix already applied to NetBrowse's build.
REM
REM --collect-all shiboken6: PySide6's own DLL-directory setup code
REM needs shiboken6's binaries fully present at a specific relative
REM location. The default PyInstaller hooks don't always grab all of
REM it, which causes an ImportError like:
REM   "...shiboken6\libshiboken does not exist"
REM at startup.
REM
REM The console window is left VISIBLE for now so
REM startup errors are visible while testing the
REM compiled build. Once you've confirmed it runs
REM correctly, add --windowed to the line below to
REM hide the console for normal use.

pyinstaller --noconfirm --clean --onedir --name CyberDeckBrowser ^
    --contents-directory "CyberDeckBrowser_internal" ^
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
    --add-data "icon.ico;." ^
    launcher.py

if errorlevel 1 (
    echo.
    echo Build failed - see the PyInstaller output above.
    pause
    exit /b 1
)

REM Strip QtWebEngine locale files down to English only - it ships
REM several dozen .pak translation files by default (one per locale),
REM most of which this app has no in-app language switcher to even
REM select. Safe to re-run; harmless if the folder isn't found.
if exist "dist\CyberDeckBrowser\PySide6\translations\qtwebengine_locales" (
    echo Trimming QtWebEngine locale files to en-US only...
    for %%F in ("dist\CyberDeckBrowser\PySide6\translations\qtwebengine_locales\*.pak") do (
        if /I not "%%~nxF"=="en-US.pak" del /q "%%F"
    )
)

if not exist "dist\CyberDeckBrowser\icon.ico" (
    copy /y "icon.ico" "dist\CyberDeckBrowser\icon.ico" >nul
)

echo.
echo ================================================
echo Build complete.
echo.
echo Your executable is at:
echo   dist\CyberDeckBrowser\CyberDeckBrowser.exe
echo.
echo Run it from that folder (not by moving just the
echo .exe elsewhere) - it needs the rest of the files
echo PyInstaller placed alongside it.
echo ================================================
pause
