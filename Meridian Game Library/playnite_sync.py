"""
Silent Playnite background sync for Meridian Game Library.

Playnite has no official headless/background mode — this is disclosed
clearly, not glossed over. What it does have, and what this module
actually uses, are three documented pieces: the --hidesplashscreen and
--shutdown command-line arguments (see Playnite's own cmdlineArguments
docs), and the fact that installing normally leaves a standard Windows
uninstall registry entry Meridian Game Library can use to find the executable without
the person having to hunt it down themselves.

The "silent" part — hiding Playnite's window the moment it appears — is a
practical trick (find its window handle via pywin32, ShowWindow SW_HIDE),
not something Playnite supports natively. Two honest limitations that
follow from that:
  - There's necessarily a brief window between the process starting and
    Meridian Game Library finding+hiding its window, so a very quick flash is possible
    on some systems.
  - If Playnite needs to show a blocking dialog (first-run wizard, an
    update prompt, a crash report), that dialog is now hidden too and
    nothing can be clicked — this module has a hard timeout specifically
    so this app's startup can't hang forever waiting on a dialog nobody
    can see. If sync keeps silently failing, open Playnite normally once
    to clear whatever's blocking it, then it should go back to working
    silently.

This whole thing is best-effort freshness, not a guarantee: it runs once
at startup in a background thread, and every section already
falls back gracefully to whatever's in the export file (however old) if
this doesn't finish in time.
"""

import os
import subprocess
import threading
import time
import winreg
from pathlib import Path

import playnite_import
import store

try:
    import win32gui
    import win32process
except ImportError:
    win32gui = None
    win32process = None


# --------------------------------------------------------------------------
# Locating the Playnite executable
# --------------------------------------------------------------------------

_COMMON_PATHS = [
    r"%LocalAppData%\Playnite\Playnite.DesktopApp.exe",
    r"%LocalAppData%\Programs\Playnite\Playnite.DesktopApp.exe",
]


def _find_via_uninstall_registry():
    """
    Normal Playnite installs register a standard Windows uninstall entry
    with an InstallLocation — this is the most reliable way to find it
    without asking the person to browse for it themselves.
    """
    roots = [
        (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
    ]
    for hive, key_path in roots:
        try:
            with winreg.OpenKey(hive, key_path) as root_key:
                i = 0
                while True:
                    try:
                        subkey_name = winreg.EnumKey(root_key, i)
                    except OSError:
                        break
                    i += 1
                    try:
                        with winreg.OpenKey(root_key, subkey_name) as subkey:
                            display_name = winreg.QueryValueEx(subkey, "DisplayName")[0]
                            if "playnite" not in display_name.lower():
                                continue
                            install_loc = winreg.QueryValueEx(subkey, "InstallLocation")[0]
                            exe_path = Path(install_loc) / "Playnite.DesktopApp.exe"
                            if exe_path.is_file():
                                return str(exe_path)
                    except OSError:
                        continue
        except OSError:
            continue
    return None


def find_playnite_executable(playnite_settings):
    override = playnite_settings.get("executable_path")
    if override and os.path.isfile(override):
        return override

    found = _find_via_uninstall_registry()
    if found:
        return found

    for candidate in _COMMON_PATHS:
        expanded = os.path.expandvars(candidate)
        if os.path.isfile(expanded):
            return expanded

    return None


# --------------------------------------------------------------------------
# Hiding the window (best-effort — see module docstring)
# --------------------------------------------------------------------------

def _hide_windows_for_pid(pid, attempts=20, delay=0.3):
    """
    Polls for any top-level window belonging to the given process and
    hides it as soon as it appears. Best-effort: if pywin32 isn't
    available, or nothing shows up in time, this silently gives up rather
    than blocking the sync — Playnite's window may just flash briefly in
    that case, which is preferable to the app hanging.
    """
    if win32gui is None:
        return

    hidden_any = False
    for _ in range(attempts):
        def _callback(hwnd, _):
            nonlocal hidden_any
            if not win32gui.IsWindowVisible(hwnd):
                return
            _, found_pid = win32process.GetWindowThreadProcessId(hwnd)
            if found_pid == pid:
                try:
                    win32gui.ShowWindow(hwnd, 0)  # SW_HIDE
                    hidden_any = True
                except Exception:
                    pass
        try:
            win32gui.EnumWindows(_callback, None)
        except Exception:
            pass
        if hidden_any:
            return
        time.sleep(delay)


# --------------------------------------------------------------------------
# The actual silent sync
# --------------------------------------------------------------------------

def silent_sync(playnite_settings, timeout=90):
    """
    Launches Playnite hidden, waits for the MeridianExporter extension to
    rewrite the export file (proof the library sync actually completed —
    Playnite auto-syncs on startup by default), then asks it to shut down
    via --shutdown. Returns True if a fresh export was observed in time.
    """
    exe_path = find_playnite_executable(playnite_settings)
    if not exe_path:
        return False

    export_path = playnite_import.get_export_path(playnite_settings)
    try:
        before_mtime = os.path.getmtime(export_path)
    except OSError:
        before_mtime = None

    try:
        proc = subprocess.Popen([exe_path, "--hidesplashscreen"])
    except OSError:
        return False

    hide_thread = threading.Thread(target=_hide_windows_for_pid, args=(proc.pid,), daemon=True)
    hide_thread.start()

    deadline = time.time() + timeout
    synced = False
    while time.time() < deadline:
        try:
            mtime = os.path.getmtime(export_path)
            if before_mtime is None or mtime > before_mtime:
                synced = True
                break
        except OSError:
            pass
        time.sleep(1)

    try:
        subprocess.Popen([exe_path, "--shutdown"])
    except OSError:
        pass

    return synced


def silent_sync_in_background(playnite_settings, timeout=90, on_done=None):
    """
    Fire-and-forget wrapper for calling this at app startup without
    blocking the UI from appearing. on_done, if given, is called with the
    bool result once finished (from the background thread — any UI update
    inside it needs to be dispatched back to the main/GUI thread itself).
    """
    def _run():
        result = silent_sync(playnite_settings, timeout=timeout)
        if on_done:
            try:
                on_done(result)
            except Exception:
                pass

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    return thread
