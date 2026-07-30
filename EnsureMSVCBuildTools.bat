@echo off
REM ============================================================
REM  EnsureMSVCBuildTools.bat
REM
REM  Detects the MSVC C++ Build Tools via vswhere and installs
REM  them (the VCTools workload) if missing. Idempotent - safe to
REM  call more than once; a second call detects "already
REM  installed" and returns immediately. Sets VCTOOLS_FOUND=1
REM  when the toolchain is present.
REM
REM  Call this (don't start it) - no setlocal, so VCTOOLS_FOUND
REM  and the detection persist to the caller. Uses the caller's
REM  %ROOT% and %TEMPDL%. Best-effort: a failed download just
REM  leaves VCTOOLS_FOUND unset and prints guidance.
REM
REM  This is the multi-GB piece the lightweight installer
REM  deliberately avoids; only the WithGameInputBuild installer
REM  (which already needs it for gameinput_native) calls it.
REM ============================================================

if not defined TEMPDL set "TEMPDL=%TEMP%\MeridianSuiteSetup"
if not exist "%TEMPDL%" mkdir "%TEMPDL%" >nul 2>nul

set "VSWHERE=%ProgramFiles(x86)%\Microsoft Visual Studio\Installer\vswhere.exe"
set "VCTOOLS_FOUND="
if exist "%VSWHERE%" (
    for /f "usebackq tokens=*" %%i in (`"%VSWHERE%" -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath 2^>nul`) do (
        if not "%%i"=="" set "VCTOOLS_FOUND=1"
    )
)

if defined VCTOOLS_FOUND (
    echo     OK - MSVC C++ Build Tools already installed ^(found via vswhere^).
    goto :msvc_done
)

echo     MSVC C++ Build Tools not found - installing ^(several GB, can take
echo     a while on a fresh machine^)...
if exist "%ROOT%Dependencies\vs_buildtools.exe" (
    copy /y "%ROOT%Dependencies\vs_buildtools.exe" "%TEMPDL%\vs_buildtools.exe" >nul
) else (
    powershell -NoProfile -Command "[Net.ServicePointManager]::SecurityProtocol='Tls12'; Invoke-WebRequest -Uri 'https://aka.ms/vs/17/release/vs_buildtools.exe' -OutFile '%TEMPDL%\vs_buildtools.exe'"
)
if exist "%TEMPDL%\vs_buildtools.exe" (
    "%TEMPDL%\vs_buildtools.exe" --quiet --wait --norestart --nocache ^
        --add Microsoft.VisualStudio.Workload.VCTools --includeRecommended
    set "VCTOOLS_FOUND=1"
    echo     OK - installed.
) else (
    echo     [WARN] Couldn't download the C++ Build Tools. Anything that needs
    echo            a C++/Rust compiler ^(gameinput_native, the native Rust
    echo            backend^) will be skipped and fall back automatically.
    echo            Install "Desktop development with C++" manually from
    echo            https://visualstudio.microsoft.com/visual-cpp-build-tools/
    echo            and re-run to try again.
)

:msvc_done
