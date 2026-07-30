@echo off
:: Launches onscreenmenu.exe from this same folder (root), but only if it
:: isn't already running - if it's already open, this does nothing instead
:: of closing it (previously toggled: killed it if already running, which
:: made repeated osm.bat launches close the overlay unexpectedly).

tasklist /fi "ImageName eq onscreenmenu.exe" /fo csv 2>NUL | find /I "onscreenmenu.exe" >NUL

if "%ERRORLEVEL%"=="0" (
    exit /b 0
) else (
    start "" "%~dp0onscreenmenu.exe" --window-mode=borderless-fullscreen
)
