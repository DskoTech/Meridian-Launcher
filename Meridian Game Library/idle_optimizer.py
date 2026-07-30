"""idle_optimizer.py — shrink Meridian Launcher's CPU/RAM footprint while it
is NOT the surface in use (i.e. a game or some other non-Meridian app is in
the foreground), then restore it the instant focus returns.

What it does while backgrounded, and ONLY while a genuinely external window
is foreground:
  * drops the process to BELOW_NORMAL priority, so a running game gets the
    CPU ahead of the idle launcher;
  * trims the working set (EmptyWorkingSet), handing idle physical RAM back
    to the OS - the pages fault back in on demand when the user returns.

What it deliberately does NOT touch:
  * audio playback - the music thread keeps running;
  * the controller poll - it keeps running at full rate so the
    bring-to-foreground button still works from the background.

"Backgrounded" here means the foreground window belongs to neither this
process nor any other Meridian-suite process. Focusing a Meridian child
(CyberDeckBrowser, onscreenmenu, a boxed section, ...) is normal in-suite
use and is treated as still-active, so the launcher backdrop keeps
animating behind an overlay rather than freezing.

Same design rationale as desktop_refocus_watcher: a cheap background poll,
never a system hook, so a bug here can at worst make this one feature
misbehave - it can never sit in or stall the real input path.
"""

import ctypes
from ctypes import wintypes
import sys
import threading
import time

IS_WINDOWS = sys.platform == "win32"

# How often to check the foreground owner. Focus transitions are rare and not
# latency-critical (the frontend has its own poll for animation pausing), so
# this can be relaxed; ~3Hz is plenty and essentially free.
POLL_INTERVAL_SECONDS = 0.3

# While backgrounded, re-trim the working set periodically: idle background
# work (audio decode, controller polling) slowly grows it back, and we want
# it to stay small the whole time we're hidden, not just at the transition.
RETRIM_INTERVAL_SECONDS = 5.0

NORMAL_PRIORITY_CLASS = 0x00000020
BELOW_NORMAL_PRIORITY_CLASS = 0x00004000

# Windows belonging to any of these processes count as "still in Meridian".
# Kept in sync with desktop_refocus_watcher._MERIDIAN_PROCESS_NAMES.
_MERIDIAN_PROCESS_NAMES = {
    "meridianlauncher.exe", "cyberdeckbrowser.exe", "onscreenmenu.exe",
    "meridian explorer.exe", "meridian filebrowse.exe",
    "meridian netbrowse.exe", "meridian game library.exe",
    "xinputtokeyboard.exe", "internallauncher.exe", "meridianpaint.exe",
}

_state = {"thread": None, "stop": False, "backgrounded": False}

if IS_WINDOWS:
    _user32 = ctypes.windll.user32
    _kernel32 = ctypes.windll.kernel32
    try:
        _psapi = ctypes.windll.psapi
    except Exception:
        _psapi = None


def _process_name_for_hwnd(hwnd):
    """Lower-cased exe name owning hwnd, via cheap direct WinAPI calls (no
    psutil), mirroring desktop_refocus_watcher's helper."""
    pid = wintypes.DWORD(0)
    _user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    if not pid.value:
        return None
    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    handle = _kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid.value)
    if not handle:
        return None
    try:
        buf = ctypes.create_unicode_buffer(260)
        size = wintypes.DWORD(260)
        if _kernel32.QueryFullProcessImageNameW(handle, 0, buf, ctypes.byref(size)):
            full_path = buf.value
            return full_path.rsplit("\\", 1)[-1].lower() if full_path else None
    except Exception:
        pass
    finally:
        _kernel32.CloseHandle(handle)
    return None


def is_suite_active():
    """True when the foreground window belongs to this process or any other
    Meridian-suite process; False when something external (a game, browser,
    desktop, ...) is in front. On non-Windows or any failure, returns True
    (never throttle when unsure)."""
    if not IS_WINDOWS:
        return True
    try:
        hwnd = _user32.GetForegroundWindow()
        if not hwnd:
            return False  # nothing focused (e.g. a fullscreen game grabbing input)
        fg_pid = wintypes.DWORD(0)
        _user32.GetWindowThreadProcessId(hwnd, ctypes.byref(fg_pid))
        if fg_pid.value == _kernel32.GetCurrentProcessId():
            return True
        name = _process_name_for_hwnd(hwnd)
        return bool(name and name in _MERIDIAN_PROCESS_NAMES)
    except Exception:
        return True


def _set_priority(priority_class):
    try:
        _kernel32.SetPriorityClass(_kernel32.GetCurrentProcess(), priority_class)
    except Exception:
        pass


def _trim_working_set():
    """Hand idle physical RAM back to the OS. EmptyWorkingSet is exactly this;
    fall back to SetProcessWorkingSetSize(-1, -1) which does the same."""
    try:
        handle = _kernel32.GetCurrentProcess()
        if _psapi is not None and hasattr(_psapi, "EmptyWorkingSet"):
            _psapi.EmptyWorkingSet(handle)
        else:
            _kernel32.SetProcessWorkingSetSize(
                handle, ctypes.c_size_t(-1), ctypes.c_size_t(-1)
            )
    except Exception:
        pass


def _enter_background():
    _state["backgrounded"] = True
    _set_priority(BELOW_NORMAL_PRIORITY_CLASS)
    _trim_working_set()


def _leave_background():
    _state["backgrounded"] = False
    _set_priority(NORMAL_PRIORITY_CLASS)
    # No un-trim needed: pages fault back in as the UI touches them.


def _loop():
    last_trim = 0.0
    while not _state["stop"]:
        try:
            active = is_suite_active()
            if not active:
                if not _state["backgrounded"]:
                    _enter_background()
                    last_trim = time.monotonic()
                elif time.monotonic() - last_trim >= RETRIM_INTERVAL_SECONDS:
                    _trim_working_set()
                    last_trim = time.monotonic()
            else:
                if _state["backgrounded"]:
                    _leave_background()
        except Exception:
            pass
        time.sleep(POLL_INTERVAL_SECONDS)


def start():
    """Start the optimizer. No-op on non-Windows or if already running."""
    if not IS_WINDOWS:
        return
    if _state["thread"] is not None and _state["thread"].is_alive():
        return
    _state["stop"] = False
    _state["thread"] = threading.Thread(target=_loop, daemon=True)
    _state["thread"].start()


def stop():
    _state["stop"] = True
    if _state["backgrounded"]:
        _leave_background()
