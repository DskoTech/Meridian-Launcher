@echo off
:: Toggle On-Screen Keyboard (osk.exe)

tasklist /fi "ImageName eq osk.exe" /fo csv 2>NUL | find /I "osk.exe" >NUL

if "%ERRORLEVEL%"=="0" (
    echo Closing On-Screen Keyboard...
    taskkill /f /im osk.exe >NUL 2>&1
) else (
    echo Opening On-Screen Keyboard...
    start "" osk.exe
)

echo Done.