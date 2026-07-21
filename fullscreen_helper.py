"""Fullscreen Helper — optional, off-by-default launch mode.

Meridian's normal launch path (system_actions.launch_path) asks Windows to
open a program maximized via the show_cmd hint. That's a *request*, not a
guarantee: well-behaved apps honor it, but plenty of third-party programs
open "maximized" while still drawing a title bar, borders, and a taskbar —
or ignore the hint entirely and restore whatever window size/position they
remember from last time.

This module is a stronger fallback for exactly that case. Instead of asking
nicely, it launches the process, finds its top-level window, strips the
window chrome (caption/border/system menu) with SetWindowLong, and resizes
it to exactly cover the monitor with SetWindowPos. That makes any ordinary
window "appear" borderless-fullscreen even if the app itself has no
fullscreen concept — including windows that only *look* maximized (chrome
still visible) under the normal launch path.

This is a blunt instrument and not what every app wants, which is why it's
a per-install, off-by-default Settings toggle ("Fullscreen Helper") rather
than the default launch behavior. It only affects .exe launches; folders,
.bat/.cmd scripts, and URLs are untouched.

Besides the initial force (plus a couple of quick reapply passes for apps
that re-assert their own window style right after opening), this also
rechecks at 5s/10s/15s after launch: if the forced window has disappeared
by then (a splash screen closing into a real window later than the quick
passes cover, an update/relaunch cycle, etc), it looks for a replacement
window belonging to the same process and forces that fullscreen too.
"""

import os
import subprocess
import threading
import time

try:
    import win32gui
    import win32process
    import win32con
    import win32api
except ImportError:  # non-Windows dev environment / missing pywin32
    win32gui = None


# How long to keep polling for the window to appear after the process
# starts. Some apps (Electron, Unity, anything with a splash screen) take
# a beat to create their real top-level window.
_FIND_WINDOW_TIMEOUT = 12.0
_POLL_INTERVAL = 0.2

# Some apps re-assert their own saved window style/position a few frames
# after creation, undoing our SetWindowPos. Reapplying once or twice more
# over the following second catches that without a permanent watcher.
_REAPPLY_DELAYS = (0.5, 1.5)


def available():
    """Whether the win32 APIs this module needs are actually importable."""
    return win32gui is not None


def _screen_rect_for_hwnd(hwnd):
    """Full pixel rect of the monitor the given window is (mostly) on, so
    multi-monitor setups get sized to the right screen rather than always
    monitor 0."""
    try:
        monitor = win32api.MonitorFromWindow(hwnd, win32con.MONITOR_DEFAULTTONEAREST)
        info = win32api.GetMonitorInfo(monitor)
        left, top, right, bottom = info["Monitor"]
        return left, top, right - left, bottom - top
    except Exception:
        # Fall back to the primary monitor's metrics.
        return 0, 0, win32api.GetSystemMetrics(0), win32api.GetSystemMetrics(1)


def _find_window_for_pid(pid, timeout=_FIND_WINDOW_TIMEOUT):
    """Poll for the first visible, titled top-level window owned by pid
    (or one of its immediate child processes, for launchers that spawn a
    separate real process and exit)."""
    deadline = time.time() + timeout
    result = {"hwnd": None}

    def callback(hwnd, _):
        if not win32gui.IsWindowVisible(hwnd):
            return True
        if win32gui.GetParent(hwnd) != 0:
            return True
        if not win32gui.GetWindowText(hwnd):
            return True
        _, found_pid = win32process.GetWindowThreadProcessId(hwnd)
        if found_pid == pid:
            result["hwnd"] = hwnd
            return False
        return True

    while time.time() < deadline and result["hwnd"] is None:
        try:
            win32gui.EnumWindows(callback, None)
        except Exception:
            pass  # EnumWindows raises pywintypes.error when we stop early
        if result["hwnd"]:
            break
        time.sleep(_POLL_INTERVAL)

    return result["hwnd"]


def _force_borderless_fullscreen(hwnd):
    style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
    style &= ~(win32con.WS_CAPTION | win32con.WS_THICKFRAME |
               win32con.WS_MINIMIZEBOX | win32con.WS_MAXIMIZEBOX |
               win32con.WS_SYSMENU)
    win32gui.SetWindowLong(hwnd, win32con.GWL_STYLE, style)

    ex_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
    ex_style &= ~(win32con.WS_EX_DLGMODALFRAME | win32con.WS_EX_WINDOWEDGE)
    win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, ex_style)

    x, y, w, h = _screen_rect_for_hwnd(hwnd)
    win32gui.SetWindowPos(
        hwnd, win32con.HWND_TOP, x, y, w, h,
        win32con.SWP_FRAMECHANGED | win32con.SWP_SHOWWINDOW,
    )
    try:
        win32gui.SetForegroundWindow(hwnd)
    except Exception:
        pass  # foreground can be denied depending on focus-stealing rules; non-fatal


# After the initial force + quick reapply passes above, keep checking at
# these points (seconds since launch) for a window that's since
# disappeared - a splash screen closing into a real window later than
# _REAPPLY_DELAYS covers, an update/relaunch cycle, a crash-and-respawn,
# etc - and force fullscreen again if a replacement window shows up.
_RECHECK_DELAYS = (5.0, 10.0, 15.0)


def _watch_and_enforce(path, args, proc):
    launch_time = time.time()
    pid = proc.pid
    hwnd = _find_window_for_pid(pid)
    if not hwnd:
        return
    _force_borderless_fullscreen(hwnd)
    for delay in _REAPPLY_DELAYS:
        time.sleep(delay)
        try:
            if not win32gui.IsWindow(hwnd):
                hwnd = None
                break
            _force_borderless_fullscreen(hwnd)
        except Exception:
            hwnd = None
            break

    for checkpoint in _RECHECK_DELAYS:
        remaining = checkpoint - (time.time() - launch_time)
        if remaining > 0:
            time.sleep(remaining)

        # The process itself exited - nothing left to enforce, and no
        # point checking later checkpoints either.
        if proc.poll() is not None:
            return

        window_lost = hwnd is None or not win32gui.IsWindow(hwnd)
        if not window_lost:
            continue  # still there and still forced from earlier - nothing to do

        # Window's gone (or was never found) - look for a new one
        # belonging to the same process and, if found, force it
        # fullscreen the same way the initial launch did. A short-ish
        # timeout here since this is a periodic recheck, not the initial
        # launch wait, which already gets the full _FIND_WINDOW_TIMEOUT.
        new_hwnd = _find_window_for_pid(pid, timeout=3.0)
        if new_hwnd:
            hwnd = new_hwnd
            try:
                _force_borderless_fullscreen(hwnd)
            except Exception:
                hwnd = None


def launch_and_enforce_fullscreen(path, args=None):
    """Launch path (an .exe), then force whatever window it opens into
    borderless fullscreen on its own monitor. Returns (ok, error) the same
    shape as system_actions.launch_path; the window-forcing itself happens
    on a background thread so this returns as soon as the process starts.
    """
    if not path or not os.path.isfile(path):
        return False, "File not found."
    if not available():
        return False, "Fullscreen Helper requires pywin32, which isn't installed."
    try:
        proc = subprocess.Popen(
            [path] + list(args or []),
            cwd=os.path.dirname(path) or None,
            shell=False,
        )
    except Exception as e:
        return False, str(e)

    threading.Thread(target=_watch_and_enforce, args=(path, args, proc), daemon=True).start()
    return True, None
