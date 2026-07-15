@echo off
setlocal enabledelayedexpansion

REM ============================================================
REM  Meridian Explorer - Windows Shell Integration
REM
REM  Makes Meridian Explorer receive the system's folder-open
REM  calls, at your choice of two levels:
REM
REM   [1] CONTEXT MENU ONLY (safe, additive)
REM       Adds "Open in Meridian Explorer" to the right-click
REM       menu of every folder and drive. Nothing else changes.
REM
REM   [2] DEFAULT FOLDER HANDLER (the true-substitute mode)
REM       Also makes Meridian Explorer the DEFAULT verb for
REM       folders and drives, so double-clicking a folder on the
REM       Desktop, and programs that ShellExecute a folder path
REM       (most "Open folder..." buttons in other software),
REM       open Meridian Explorer instead of Windows Explorer.
REM       HONEST LIMITS: navigation *inside* an already-open
REM       Windows Explorer window stays in Windows Explorer
REM       (that never goes through the shell verb), and so do
REM       apps that hard-code explorer.exe. Everything routed
REM       through the standard folder association comes to
REM       Meridian Explorer.
REM
REM   [3] REMOVE - restore Windows defaults completely.
REM
REM  All changes live under HKCU\Software\Classes (current user
REM  only), so no Administrator is needed and nothing touches
REM  other accounts. Fully reversible with option [3].
REM ============================================================

set "ROOT=%~dp0"

REM Find Meridian Explorer.exe: next to this script first (repo/DskoTech
REM layout), then the standard install location.
set "MX=%ROOT%Meridian Explorer.exe"
if not exist "%MX%" set "MX=C:\Program Files\DskoTech\Meridian Explorer.exe"
if not exist "%MX%" (
    echo [ERROR] "Meridian Explorer.exe" wasn't found next to this script
    echo         or in C:\Program Files\DskoTech.
    echo         Put this script in the DskoTech folder ^(or repo root with
    echo         a built exe^) and run it again.
    pause
    exit /b 1
)

echo ============================================================
echo  Meridian Explorer - Shell Integration
echo  Using: %MX%
echo ============================================================
echo.
echo   [1] Add "Open in Meridian Explorer" to folder right-click menus
echo   [2] Make Meridian Explorer the DEFAULT folder handler
echo   [3] Remove integration (restore Windows defaults)
echo   [Q] Quit without changes
echo.
choice /c 123Q /n /m "Pick an option: "
if errorlevel 4 exit /b 0
if errorlevel 3 goto :remove
if errorlevel 2 goto :default_handler
if errorlevel 1 goto :context_menu

:context_menu
echo.
echo Adding context-menu entries...
reg add "HKCU\Software\Classes\Directory\shell\MeridianExplorer" /ve /d "Open in Meridian Explorer" /f >nul
reg add "HKCU\Software\Classes\Directory\shell\MeridianExplorer" /v Icon /d "\"%MX%\"" /f >nul
reg add "HKCU\Software\Classes\Directory\shell\MeridianExplorer\command" /ve /d "\"%MX%\" \"%%1\"" /f >nul
reg add "HKCU\Software\Classes\Drive\shell\MeridianExplorer" /ve /d "Open in Meridian Explorer" /f >nul
reg add "HKCU\Software\Classes\Drive\shell\MeridianExplorer" /v Icon /d "\"%MX%\"" /f >nul
reg add "HKCU\Software\Classes\Drive\shell\MeridianExplorer\command" /ve /d "\"%MX%\" \"%%1\"" /f >nul
reg add "HKCU\Software\Classes\Directory\Background\shell\MeridianExplorer" /ve /d "Open in Meridian Explorer" /f >nul
reg add "HKCU\Software\Classes\Directory\Background\shell\MeridianExplorer\command" /ve /d "\"%MX%\" \"%%V\"" /f >nul
echo Done - right-click any folder, drive, or folder background for
echo "Open in Meridian Explorer". Windows defaults untouched.
goto :end

:default_handler
echo.
echo Adding context-menu entries AND making Meridian Explorer the
echo default folder handler...
call :context_menu_silent
REM Setting the shell key's default value to our verb name makes it the
REM default action (what double-click / ShellExecute-open resolves to).
reg add "HKCU\Software\Classes\Directory\shell" /ve /d "MeridianExplorer" /f >nul
reg add "HKCU\Software\Classes\Drive\shell" /ve /d "MeridianExplorer" /f >nul
echo.
echo Done. Folder opens routed through the standard shell association -
echo Desktop double-clicks, "Open folder" buttons in other programs -
echo now open Meridian Explorer. Note: browsing INSIDE an already-open
echo Windows Explorer window stays in Windows Explorer; that navigation
echo never leaves Explorer's own process.
goto :end

:context_menu_silent
reg add "HKCU\Software\Classes\Directory\shell\MeridianExplorer" /ve /d "Open in Meridian Explorer" /f >nul
reg add "HKCU\Software\Classes\Directory\shell\MeridianExplorer" /v Icon /d "\"%MX%\"" /f >nul
reg add "HKCU\Software\Classes\Directory\shell\MeridianExplorer\command" /ve /d "\"%MX%\" \"%%1\"" /f >nul
reg add "HKCU\Software\Classes\Drive\shell\MeridianExplorer" /ve /d "Open in Meridian Explorer" /f >nul
reg add "HKCU\Software\Classes\Drive\shell\MeridianExplorer" /v Icon /d "\"%MX%\"" /f >nul
reg add "HKCU\Software\Classes\Drive\shell\MeridianExplorer\command" /ve /d "\"%MX%\" \"%%1\"" /f >nul
reg add "HKCU\Software\Classes\Directory\Background\shell\MeridianExplorer" /ve /d "Open in Meridian Explorer" /f >nul
reg add "HKCU\Software\Classes\Directory\Background\shell\MeridianExplorer\command" /ve /d "\"%MX%\" \"%%V\"" /f >nul
goto :eof

:remove
echo.
echo Removing all Meridian Explorer shell integration...
REM Clear the default-verb overrides first (restores Windows' default
REM folder open), then remove our verb keys entirely.
reg delete "HKCU\Software\Classes\Directory\shell" /ve /f >nul 2>&1
reg delete "HKCU\Software\Classes\Drive\shell" /ve /f >nul 2>&1
reg delete "HKCU\Software\Classes\Directory\shell\MeridianExplorer" /f >nul 2>&1
reg delete "HKCU\Software\Classes\Drive\shell\MeridianExplorer" /f >nul 2>&1
reg delete "HKCU\Software\Classes\Directory\Background\shell\MeridianExplorer" /f >nul 2>&1
echo Done - Windows Explorer is the folder handler again.
goto :end

:end
echo.
pause
exit /b 0
