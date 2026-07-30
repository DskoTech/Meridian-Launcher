@echo off
REM ============================================================
REM  EnsureRustToolchain.bat
REM
REM  Makes sure `cargo` is available on PATH for the CURRENT
REM  session, installing Rust via rustup (unattended, minimal)
REM  if needed. Sets CARGO_OK=1 on success.
REM
REM  IMPORTANT: call this (call "...EnsureRustToolchain.bat"),
REM  don't start it - it intentionally does NOT use setlocal, so
REM  the PATH/CARGO_OK it sets persist back to the caller.
REM
REM  Best-effort: if anything fails it just leaves CARGO_OK unset
REM  and the apps fall back to pure Python. Rust's default
REM  windows-msvc toolchain needs the MSVC C++ linker to actually
REM  build - the caller is responsible for ensuring that.
REM ============================================================

set "CARGO_OK="

where cargo >nul 2>nul
if not errorlevel 1 (
    set "CARGO_OK=1"
    echo     OK - Rust already on PATH.
    goto :rust_done
)

REM Installed previously but not on this session's PATH yet?
if exist "%USERPROFILE%\.cargo\bin\cargo.exe" (
    set "PATH=%USERPROFILE%\.cargo\bin;%PATH%"
    set "CARGO_OK=1"
    echo     OK - found existing Rust in %%USERPROFILE%%\.cargo\bin.
    goto :rust_done
)

echo     Rust not found - installing via rustup ^(minimal, unattended^)...
powershell -NoProfile -Command "[Net.ServicePointManager]::SecurityProtocol='Tls12'; Invoke-WebRequest -Uri 'https://win.rustup.rs/x86_64' -OutFile '%TEMP%\rustup-init.exe'"
if not exist "%TEMP%\rustup-init.exe" (
    echo     [WARN] Couldn't download rustup-init.exe - skipping the native
    echo            backend ^(pure-Python fallback still works fine^).
    goto :rust_done
)

"%TEMP%\rustup-init.exe" -y --default-toolchain stable --profile minimal --no-modify-path
if exist "%USERPROFILE%\.cargo\bin\cargo.exe" (
    set "PATH=%USERPROFILE%\.cargo\bin;%PATH%"
    set "CARGO_OK=1"
    echo     OK - Rust installed.
) else (
    echo     [WARN] Rust install did not complete - native backend skipped
    echo            ^(pure-Python fallback used, everything still works^).
)

:rust_done
