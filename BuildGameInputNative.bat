@echo off
REM ============================================================
REM  BuildGameInputNative.bat
REM
REM  Builds gameinput_native.pyd (the real Microsoft GameInput SDK
REM  backend — fixes the Xbox One Bluetooth silent-input bug and
REM  replaces the old ctypes vtable-guessing implementation) and
REM  deploys it next to gameinput_api.py in every app folder.
REM
REM  IDEMPOTENT: if a .pyd built against THIS Python already exists
REM  next to gameinput_api.py at the repo root, the build is skipped
REM  so re-running the installer doesn't recompile unnecessarily.
REM
REM  BEST-EFFORT: every failure path prints a clear [WARN] and exits
REM  with code 1, but nothing in the calling installer treats that as
REM  fatal. Controller input keeps working via the XInput fallback in
REM  gameinput_api.py; this just makes it more reliable (especially
REM  for Xbox One over Bluetooth and PlayStation controllers).
REM
REM  REQUIREMENTS:
REM    - Python on PATH (same interpreter the apps were built with)
REM    - MSVC C++ Build Tools ("Desktop development with C++" workload)
REM    - pybind11 Python package (pip install pybind11)
REM    All three must be present; EnsureMSVCBuildTools.bat handles the
REM    second one. The calling installer installs pybind11 via pip.
REM
REM  CALLED BY:
REM    InstallMeridianSuite.bat          (when MSVC is already present)
REM    InstallMeridianSuite_WithGameInputBuild.bat  (always)
REM    CompileAndPackage.bat             (step [0b])
REM    quickcompile.bat                  (step [0b])
REM ============================================================

setlocal enabledelayedexpansion

set "ROOT=%~dp0"
set "GI_DIR=%ROOT%gameinput_native"
set "GI_BUILT="
set "GI_SKIPPED="

REM ---- Resolve Python ----------------------------------------
set "PYTHON_EXE="
for /f "delims=" %%P in ('where python 2^>nul') do (
    if not defined PYTHON_EXE set "PYTHON_EXE=%%P"
)
if not defined PYTHON_EXE (
    echo     [WARN] Python not found on PATH - cannot build gameinput_native.
    echo            Controller input will use the XInput / ctypes fallback.
    endlocal & exit /b 1
)

REM ---- Already built for this Python? -------------------------
REM  gameinput_native.cp<pyver>-win_amd64.pyd in the repo root means a
REM  prior run already did this. We check root (not the gameinput_native/
REM  source folder) because that's where the apps and the installer's
REM  staging step expect to find it.
for %%F in ("%ROOT%gameinput_native.cp*-win_amd64.pyd") do (
    set "GI_SKIPPED=1"
)
if defined GI_SKIPPED (
    echo     OK - gameinput_native.pyd already built ^(skipping recompile^).
    endlocal & exit /b 0
)

REM ---- MSVC toolchain present? --------------------------------
set "VSWHERE=%ProgramFiles(x86)%\Microsoft Visual Studio\Installer\vswhere.exe"
set "VCTOOLS="
if exist "%VSWHERE%" (
    for /f "usebackq tokens=*" %%i in (
        `"%VSWHERE%" -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath 2^>nul`
    ) do (
        if not "%%i"=="" set "VCTOOLS=1"
    )
)
if not defined VCTOOLS (
    echo     [WARN] MSVC C++ Build Tools not found - cannot compile gameinput_native.
    echo            Run InstallMeridianSuite_WithGameInputBuild.bat to install them
    echo            automatically, or install "Desktop development with C++" from
    echo            https://visualstudio.microsoft.com/visual-cpp-build-tools/
    echo            Controller input will use the XInput / ctypes fallback.
    endlocal & exit /b 1
)

REM ---- pybind11 installed? ------------------------------------
"%PYTHON_EXE%" -c "import pybind11" >nul 2>nul
if errorlevel 1 (
    echo     pybind11 not found - installing...
    "%PYTHON_EXE%" -m pip install pybind11 --break-system-packages --quiet
    "%PYTHON_EXE%" -c "import pybind11" >nul 2>nul
    if errorlevel 1 (
        echo     [WARN] pybind11 install failed - cannot build gameinput_native.
        echo            Try:  pip install pybind11 --break-system-packages
        echo            Controller input will use the XInput / ctypes fallback.
        endlocal & exit /b 1
    )
    echo     OK - pybind11 installed.
)

REM ---- Build --------------------------------------------------
echo     Building gameinput_native.pyd ^(C++ + real GameInput SDK^)...
echo     ^(This takes ~30s on first build; subsequent installs skip it.^)
pushd "%GI_DIR%"
"%PYTHON_EXE%" build_and_deploy.py
set "BUILD_RC=%ERRORLEVEL%"
popd

if %BUILD_RC% neq 0 (
    echo     [WARN] gameinput_native build failed ^(see compiler output above^).
    echo            This is non-fatal: controller input still works via the
    echo            XInput fallback. Common causes:
    echo              - MSVC linker not on PATH ^(open a "Developer Command
    echo                Prompt for VS" and re-run from there, or let
    echo                EnsureMSVCBuildTools.bat set up the environment^)
    echo              - gameinput_native/ source folder missing files
    echo            Re-run this installer after fixing, or build manually:
    echo              cd gameinput_native ^&^& python build_and_deploy.py
    endlocal & exit /b 1
)

REM ---- Confirm the .pyd landed in the repo root ---------------
set "GI_BUILT="
for %%F in ("%ROOT%gameinput_native.cp*-win_amd64.pyd") do set "GI_BUILT=1"
if not defined GI_BUILT (
    echo     [WARN] Build reported success but no gameinput_native*.pyd
    echo            appeared at the repo root. Check that build_and_deploy.py
    echo            completed its copy steps ^(FAIL lines above^).
    endlocal & exit /b 1
)

echo     OK - gameinput_native.pyd built and deployed to all app folders.
endlocal & exit /b 0
