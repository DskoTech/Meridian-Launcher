@echo off
:: Silent Toggle for onscreenmenu.exe (local folder)

tasklist /fi "ImageName eq onscreenmenu.exe" /fo csv 2>NUL | find /I "onscreenmenu.exe" >NUL

if "%ERRORLEVEL%"=="0" (
    taskkill /f /im onscreenmenu.exe >NUL 2>&1
) else (
    start "" "%~dp0onscreenmenu.exe" --window-mode=borderless-fullscreen
)