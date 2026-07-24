"""desktop_refocus_watcher.py — clicking the real Windows desktop
background (or any window that isn't part of the Meridian suite) while
some other program currently has focus brings Meridian Launcher back to
the foreground. Meridian Launcher is meant to be the "home" surface for
a couch/kiosk setup, so a stray click that lands on truly empty space
should return to it rather than leaving that emptiness showing.

Deliberately narrow: a click on any OTHER real external program's own
window - something legitimately being used - must never yank focus away
from it. Only the desktop background (Progman/WorkerW) or no window at
all under the cursor counts as "void"; every other window, Meridian's
own or not, is left alone.

IMPLEMENTATION NOTE - why polling, not a hook: the first version of this
used a system-wide low-level mouse hook (WH_MOUSE_LL). That turned out
to be the wrong tool for this: a WH_MOUSE_LL hook runs SYNCHRONOUSLY in
the middle of Windows' own input pipeline for every single mouse event
on the entire system, before that event reaches ANY window, including
this one's own gamepad-to-mouse translation - any slowness, an
exception that doesn't get handled fast enough, or the installing
thread's message loop stalling for any reason shows up as system-wide
mouse lag or a full input freeze, not just a bug local to this feature.
That's exactly the class of regression a hook-based version of this
caused. Polling GetAsyncKeyState() for a button-down edge on a plain
background thread achieves the same goal without ever sitting in the
real input path at all - worst case if this code has a bug, the refocus
feature itself misbehaves; it cannot freeze or delay real mouse input
system-wide, because it never intercepts anything, only reads state.
"""

import ctypes
from ctypes import wintypes
import sys
import threading
import time

IS_WINDOWS = sys.platform == "win32"

POLL_INTERVAL_SECONDS = 0.05  # 20Hz - fast enough to feel instant, cheap enough to never matter
VK_LBUTTON = 0x01
VK_RBUTTON = 0x02
GA_ROOT = 2

# The actual Windows desktop's own window classes - a click that lands on
# either of these is unambiguously "the background", not some other real
# window that just happens not to be part of the Meridian suite.
_DESKTOP_CLASSES = {"progman", "workerw"}

# Other processes that count as "part of Meridian" - a click on one of
# these (or one of them having focus) is normal use, not "clicked the
# background", so it must never trigger a refocus.
_MERIDIAN_PROCESS_NAMES = {
    "meridianlauncher.exe", "cyberdeckbrowser.exe", "onscreenmenu.exe",
    "meridian explorer.exe", "meridian filebrowse.exe",
    "meridian netbrowse.exe", "meridian game library.exe",
    "xinputtokeyboard.exe", "internallauncher.exe", "meridianpaint.exe",
}

_state = {"thread": None, "stop": False}


class _POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


if IS_WINDOWS:
    _user32 = ctypes.windll.user32
    _kernel32 = ctypes.windll.kernel32


def _process_name_for_hwnd(hwnd):
    """Lightweight, no psutil - constructing a psutil.Process object per
    call has real overhead versus a couple of direct WinAPI calls, and
    this deliberately stays as cheap as possible even though it's off
    the real input path now (see module docstring), since it can still
    run several times a second while polling."""
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


def _own_top_level_window():
    """First visible top-level window belonging to THIS process."""
    own_pid = _kernel32.GetCurrentProcessId()
    found = []
    EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

    def _cb(hwnd, _lparam):
        pid = wintypes.DWORD(0)
        _user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value == own_pid and _user32.IsWindowVisible(hwnd):
            length = _user32.GetWindowTextLengthW(hwnd)
            if length > 0:
                found.append(hwnd)
                return False
        return True

    try:
        _user32.EnumWindows(EnumWindowsProc(_cb), 0)
    except Exception:
        pass
    return found[0] if found else None


def _class_name(hwnd):
    buf = ctypes.create_unicode_buffer(256)
    _user32.GetClassNameW(hwnd, buf, 256)
    return (buf.value or "").lower()


def _handle_click():
    """Cheap checks first (no process lookups at all) - the vast
    majority of clicks are on some real, legitimate window, and this
    exits after a couple of fast WinAPI calls for all of those. Only a
    genuine "void" click goes on to check what currently has focus."""
    pt = _POINT()
    _user32.GetCursorPos(ctypes.byref(pt))
    hwnd_at_click = _user32.WindowFromPoint(pt)
    root = _user32.GetAncestor(hwnd_at_click, GA_ROOT) if hwnd_at_click else None

    is_void = (not hwnd_at_click) or (bool(root) and _class_name(root) in _DESKTOP_CLASSES)
    if not is_void:
        return

    fg = _user32.GetForegroundWindow()
    fg_name = _process_name_for_hwnd(fg) if fg else None
    fg_is_meridian = fg_name in _MERIDIAN_PROCESS_NAMES if fg_name else False
    if fg_is_meridian:
        return

    own = _own_top_level_window()
    if own:
        _user32.SetForegroundWindow(own)


def _poll_loop():
    was_l_down = False
    was_r_down = False
    while not _state["stop"]:
        try:
            l_down = bool(_user32.GetAsyncKeyState(VK_LBUTTON) & 0x8000)
            r_down = bool(_user32.GetAsyncKeyState(VK_RBUTTON) & 0x8000)
            if (l_down and not was_l_down) or (r_down and not was_r_down):
                _handle_click()
            was_l_down, was_r_down = l_down, r_down
        except Exception:
            pass
        time.sleep(POLL_INTERVAL_SECONDS)


def start():
    """Starts the poll loop on its own daemon thread. Safe to call once
    at app startup; does nothing on non-Windows or if already running."""
    if not IS_WINDOWS or _state["thread"] is not None:
        return
    _state["stop"] = False
    t = threading.Thread(target=_poll_loop, daemon=True)
    _state["thread"] = t
    t.start()


def stop():
    _state["stop"] = True
