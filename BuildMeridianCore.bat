@echo off
REM ============================================================
REM  BuildMeridianCore.bat
REM
REM  Compiles the native Rust backend (meridian_core/) into a
REM  Python extension module and stages it as meridian_core.pyd
REM  next to BOTH main.py (Meridian Launcher) and
REM  "Meridian Game Library\main.py", so PyInstaller bundles it
REM  into each app.
REM
REM  This is BEST-EFFORT. If Rust isn't installed or the build
REM  fails, the two apps still compile and run fine — every
REM  function that uses meridian_core keeps a pure-Python
REM  fallback (see the try/except around "import meridian_core"
REM  in main.py / store.py / playnite_import.py). You just don't
REM  get the native speedups until this succeeds.
REM
REM  Requires the Rust toolchain (cargo + rustc). Install once
REM  from https://rustup.rs (the installer downloads from
REM  static.rust-lang.org). The MSVC "Build Tools for Visual
REM  Studio" C++ toolchain you already use for gameinput_native
REM  is the same linker Rust needs on Windows.
REM ============================================================

setlocal enabledelayedexpansion
set "ROOT=%~dp0"
set "CORE=%ROOT%meridian_core"
set "GL=%ROOT%Meridian Game Library"

echo.
echo === Building native core (meridian_core) ===

where cargo >nul 2>nul
if errorlevel 1 (
    echo [WARN] Rust ^(cargo^) was not found on PATH.
    echo        Skipping native core build - the apps will fall back to
    echo        their pure-Python implementations and still work.
    echo        To enable the native backend, install Rust from
    echo        https://rustup.rs and re-run this ^(or your build script^).
    endlocal
    exit /b 1
)

REM Point PyO3 at the SAME interpreter the rest of the build/PyInstaller
REM uses, so the compiled extension matches that Python's ABI.
set "PYTHON_EXE="
for /f "delims=" %%P in ('where python 2^>nul') do (
    if not defined PYTHON_EXE set "PYTHON_EXE=%%P"
)
if defined PYTHON_EXE (
    set "PYO3_PYTHON=%PYTHON_EXE%"
    echo Using Python: %PYTHON_EXE%
)

echo Running: cargo build --release
cargo build --release --manifest-path "%CORE%\Cargo.toml"
if errorlevel 1 (
    echo [WARN] cargo build failed - see the output above. The apps will
    echo        fall back to pure Python. ^(A common first-time cause on
    echo        Windows is a missing MSVC C++ linker - install the
    echo        "Desktop development with C++" workload / VS Build Tools.^)
    endlocal
    exit /b 1
)

set "DLL=%CORE%\target\release\meridian_core.dll"
if not exist "%DLL%" (
    echo [WARN] Build reported success but %DLL% is missing. Skipping.
    endlocal
    exit /b 1
)

echo Staging meridian_core.pyd next to each app...
copy /y "%DLL%" "%ROOT%meridian_core.pyd" >nul
if errorlevel 1 (
    echo [WARN] Couldn't copy meridian_core.pyd to repo root.
    endlocal
    exit /b 1
)
copy /y "%DLL%" "%GL%\meridian_core.pyd" >nul
if errorlevel 1 (
    echo [WARN] Couldn't copy meridian_core.pyd to Game Library folder.
    endlocal
    exit /b 1
)

REM Sanity check: can the interpreter actually import it?
REM  Use pushd/popd so the import test runs from the repo root - that way
REM  'import meridian_core' finds the freshly staged .pyd without needing
REM  sys.path manipulation, and we avoid embedding %ROOT% (which may
REM  contain parentheses or spaces) inside a -c string.
if defined PYTHON_EXE (
    pushd "%ROOT%"
    "%PYTHON_EXE%" -c "import meridian_core; print('   import OK - meridian_core', meridian_core.__version__)"
    if errorlevel 1 (
        popd
        echo [WARN] The built module did not import cleanly. It will be
        echo        ignored at runtime ^(pure-Python fallback^). This usually
        echo        means it was built against a different Python than the
        echo        one on PATH now.
        endlocal
        exit /b 1
    )
    popd
)

echo   OK - meridian_core.pyd staged for Launcher and Game Library.
endlocal
exit /b 0
