@echo off
:: Copy Meridian_Exporter folder to Playnite Extensions

set "SOURCE=Meridian_Exporter"
set "DEST=%AppData%\Playnite\Extensions"

echo Copying Meridian_Exporter to Playnite Extensions...

if not exist "%SOURCE%" (
    echo ERROR: Folder "%SOURCE%" not found in current directory!
    pause
    exit /b 1
)

:: Create destination folder if it doesn't exist
if not exist "%DEST%" mkdir "%DEST%"

:: Copy the folder (with subfolders and files)
xcopy "%SOURCE%" "%DEST%\%SOURCE%\" /E /I /Y /Q

echo.
echo Done! Meridian_Exporter has been copied to:
echo %DEST%\%SOURCE%
echo.
pause