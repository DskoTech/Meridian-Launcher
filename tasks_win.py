"""
tasks_win.py — enumerate the user's open, taskbar-visible windows and pull
each one's taskbar icon, for Meridian Launcher's open-programs bar.

Pure ctypes + Pillow (both already dependencies), Windows-only: every
public function degrades to a no-op/empty result on other platforms or on
any per-window failure, so a weird window can never take the bar down.

The filtering below mirrors what the real Windows taskbar shows: visible,
non-cloaked, top-level, unowned (or owner-invisible) windows without the
WS_EX_TOOLWINDOW style, that have a title.
"""

import base64
import io
import os
import sys

try:
    import psutil
except ImportError:
    psutil = None

IS_WINDOWS = sys.platform == "win32"

if IS_WINDOWS:
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    gdi32 = ctypes.windll.gdi32
    kernel32 = ctypes.windll.kernel32
    dwmapi = ctypes.windll.dwmapi

    WS_EX_TOOLWINDOW = 0x00000080
    WS_EX_APPWINDOW = 0x00040000
    GWL_EXSTYLE = -20
    GW_OWNER = 4
    DWMWA_CLOAKED = 14

    WM_GETICON = 0x007F
    ICON_SMALL = 0
    ICON_BIG = 1
    ICON_SMALL2 = 2
    GCLP_HICON = -14
    GCLP_HICONSM = -34
    SMTO_ABORTIFHUNG = 0x0002

    WM_CLOSE = 0x0010
    SW_RESTORE = 9

    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000

    EnumWindowsProc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)


def _is_taskbar_window(hwnd):
    """Same visibility rules the Windows taskbar itself uses (close enough)."""
    if not user32.IsWindowVisible(hwnd):
        return False
    # cloaked (e.g. suspended UWP apps, windows on other virtual desktops
    # are NOT cloaked so they stay — same as the real taskbar)
    cloaked = wintypes.DWORD(0)
    try:
        dwmapi.DwmGetWindowAttribute(hwnd, DWMWA_CLOAKED,
                                     ctypes.byref(cloaked), ctypes.sizeof(cloaked))
        if cloaked.value:
            return False
    except Exception:
        pass
    ex = user32.GetWindowLongPtrW(hwnd, GWL_EXSTYLE) if hasattr(user32, "GetWindowLongPtrW") \
        else user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
    if ex & WS_EX_APPWINDOW:
        pass  # explicitly asks to be on the taskbar
    elif ex & WS_EX_TOOLWINDOW:
        return False
    else:
        owner = user32.GetWindow(hwnd, GW_OWNER)
        if owner and user32.IsWindowVisible(owner):
            return False
    if user32.GetWindowTextLengthW(hwnd) == 0:
        return False
    return True


def _window_title(hwnd):
    n = user32.GetWindowTextLengthW(hwnd)
    buf = ctypes.create_unicode_buffer(n + 1)
    user32.GetWindowTextW(hwnd, buf, n + 1)
    return buf.value


def _window_pid(hwnd):
    pid = wintypes.DWORD(0)
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    return pid.value


def _exe_path(pid):
    try:
        h = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if not h:
            return None
        try:
            size = wintypes.DWORD(1024)
            buf = ctypes.create_unicode_buffer(size.value)
            if kernel32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(size)):
                return buf.value
        finally:
            kernel32.CloseHandle(h)
    except Exception:
        pass
    return None


def _get_hicon(hwnd):
    """The icon the taskbar would show for this window, best-effort."""
    result = wintypes.DWORD_PTR() if hasattr(wintypes, "DWORD_PTR") else ctypes.c_size_t()
    for which in (ICON_SMALL2, ICON_SMALL, ICON_BIG):
        try:
            if user32.SendMessageTimeoutW(hwnd, WM_GETICON, which, 0,
                                          SMTO_ABORTIFHUNG, 200, ctypes.byref(result)) and result.value:
                return result.value
        except Exception:
            pass
    for which in (GCLP_HICONSM, GCLP_HICON):
        try:
            h = user32.GetClassLongPtrW(hwnd, which) if hasattr(user32, "GetClassLongPtrW") \
                else user32.GetClassLongW(hwnd, which)
            if h:
                return h
        except Exception:
            pass
    return None


def _hicon_to_png_data_url(hicon, size=32):
    """Draw an HICON into a 32-bit DIB and hand it to Pillow -> data URL."""
    try:
        from PIL import Image
    except ImportError:
        return None

    class BITMAPINFOHEADER(ctypes.Structure):
        _fields_ = [("biSize", wintypes.DWORD), ("biWidth", wintypes.LONG),
                    ("biHeight", wintypes.LONG), ("biPlanes", wintypes.WORD),
                    ("biBitCount", wintypes.WORD), ("biCompression", wintypes.DWORD),
                    ("biSizeImage", wintypes.DWORD), ("biXPelsPerMeter", wintypes.LONG),
                    ("biYPelsPerMeter", wintypes.LONG), ("biClrUsed", wintypes.DWORD),
                    ("biClrImportant", wintypes.DWORD)]

    hdc_screen = user32.GetDC(None)
    hdc = gdi32.CreateCompatibleDC(hdc_screen)
    bmi = BITMAPINFOHEADER()
    bmi.biSize = ctypes.sizeof(BITMAPINFOHEADER)
    bmi.biWidth = size
    bmi.biHeight = -size  # top-down
    bmi.biPlanes = 1
    bmi.biBitCount = 32
    bmi.biCompression = 0  # BI_RGB
    bits = ctypes.c_void_p()
    hbmp = gdi32.CreateDIBSection(hdc, ctypes.byref(bmi), 0, ctypes.byref(bits), None, 0)
    if not hbmp:
        gdi32.DeleteDC(hdc)
        user32.ReleaseDC(None, hdc_screen)
        return None
    old = gdi32.SelectObject(hdc, hbmp)
    try:
        # DI_NORMAL = 3; leaves transparent pixels at alpha 0 in the DIB
        user32.DrawIconEx(hdc, 0, 0, hicon, size, size, 0, None, 3)
        buf = ctypes.string_at(bits, size * size * 4)
        img = Image.frombuffer("RGBA", (size, size), buf, "raw", "BGRA", 0, 1)
        # Icons drawn without an alpha channel come out fully transparent;
        # detect that and treat the image as opaque instead of invisible.
        if img.getextrema()[3][1] == 0:
            img = Image.frombuffer("RGB", (size, size), buf, "raw", "BGRX", 0, 1).convert("RGBA")
        out = io.BytesIO()
        img.save(out, format="PNG")
        return "data:image/png;base64," + base64.b64encode(out.getvalue()).decode("ascii")
    except Exception:
        return None
    finally:
        gdi32.SelectObject(hdc, old)
        gdi32.DeleteObject(hbmp)
        gdi32.DeleteDC(hdc)
        user32.ReleaseDC(None, hdc_screen)


def _exe_icon_data_url(exe_path, size=32):
    """Fallback: the icon embedded in the exe file itself (what the taskbar
    shows when a window doesn't provide one)."""
    if not exe_path:
        return None
    try:
        shell32 = ctypes.windll.shell32
        large = ctypes.c_void_p()
        small = ctypes.c_void_p()
        n = shell32.ExtractIconExW(exe_path, 0, ctypes.byref(large), ctypes.byref(small), 1)
        hicon = small.value or large.value if n else None
        if not hicon:
            return None
        try:
            return _hicon_to_png_data_url(hicon, size)
        finally:
            for h in (large.value, small.value):
                if h:
                    user32.DestroyIcon(h)
    except Exception:
        return None


# icon cache: keyed by exe path (stable across windows of the same app),
# falling back to hwnd for windows whose exe couldn't be resolved
_icon_cache = {}

# psutil.Process cache keyed by pid, for cpu_percent(). psutil's own
# cpu_percent(interval=None) is non-blocking but returns 0.0 on the FIRST
# call for a given Process object (it's measuring the delta since the
# last call, and there isn't one yet) - caching the Process object across
# polls (the taskbar polls every 2.5s) is what makes the number real
# after the first read instead of permanently reading 0%.
_proc_cache = {}


def _resource_usage(pid):
    """{"cpu_percent": float, "mem_mb": float} for a pid, best-effort.
    Returns None if psutil isn't available or the process can't be read
    (e.g. it exited between EnumWindows and here, or it's a protected
    system process this one can't query)."""
    if psutil is None:
        return None
    try:
        proc = _proc_cache.get(pid)
        if proc is None or proc.pid != pid:
            proc = psutil.Process(pid)
            proc.cpu_percent(None)  # prime the delta - see comment above
            _proc_cache[pid] = proc
            return {"cpu_percent": 0.0, "mem_mb": round(proc.memory_info().rss / (1024 * 1024), 1)}
        cpu = proc.cpu_percent(None)
        # Normalize to "percent of one core out of all cores", matching
        # how Windows' own Task Manager reports total CPU% (not per-core
        # totals that can exceed 100%), which is what most people expect
        # when comparing this against the real Task Manager.
        cpu = round(cpu / max(psutil.cpu_count() or 1, 1), 1)
        mem_mb = round(proc.memory_info().rss / (1024 * 1024), 1)
        return {"cpu_percent": cpu, "mem_mb": mem_mb}
    except Exception:
        _proc_cache.pop(pid, None)
        return None


def list_open_tasks():
    """[{id, title, exe}] plus 'icon' as a PNG data URL when one could be
    pulled. Excludes this process's own windows (the launcher shouldn't
    list itself in its own taskbar)."""
    if not IS_WINDOWS:
        return []
    own_pid = os.getpid()
    tasks = []

    @EnumWindowsProc
    def _cb(hwnd, _):
        try:
            if not _is_taskbar_window(hwnd):
                return True
            pid = _window_pid(hwnd)
            if pid == own_pid:
                return True
            title = _window_title(hwnd)
            exe = _exe_path(pid)
            cache_key = exe or f"hwnd:{hwnd}"
            icon = _icon_cache.get(cache_key)
            if icon is None:
                hicon = _get_hicon(hwnd)
                icon = _hicon_to_png_data_url(hicon) if hicon else None
                if not icon:
                    icon = _exe_icon_data_url(exe)
                _icon_cache[cache_key] = icon or ""
            tasks.append({
                "id": int(hwnd),
                "title": title,
                "exe": os.path.basename(exe) if exe else None,
                "icon": icon or None,
                "pid": pid,
                "resources": _resource_usage(pid),
            })
        except Exception:
            pass  # one bad window must never break the whole list
        return True

    try:
        user32.EnumWindows(_cb, 0)
    except Exception:
        pass
    # Drop cached Process objects for pids no longer in the open-window
    # list, so a long session doesn't slowly accumulate handles to
    # processes that closed a while ago.
    live_pids = {t["pid"] for t in tasks}
    for stale_pid in [p for p in _proc_cache if p not in live_pids]:
        _proc_cache.pop(stale_pid, None)
    return tasks


def focus_task(hwnd):
    """Bring a window to the foreground, restoring it if minimized —
    what clicking its taskbar button would do."""
    if not IS_WINDOWS:
        return False
    try:
        hwnd = int(hwnd)
        if user32.IsIconic(hwnd):
            user32.ShowWindow(hwnd, SW_RESTORE)
        # the usual trick so SetForegroundWindow is honored from an
        # unfocused process: briefly attach to the foreground thread
        fg = user32.GetForegroundWindow()
        if fg:
            fg_thread = user32.GetWindowThreadProcessId(fg, None)
            our_thread = kernel32.GetCurrentThreadId()
            user32.AttachThreadInput(our_thread, fg_thread, True)
            user32.SetForegroundWindow(hwnd)
            user32.AttachThreadInput(our_thread, fg_thread, False)
        else:
            user32.SetForegroundWindow(hwnd)
        return True
    except Exception:
        return False


def close_task(hwnd):
    """Politely ask the window to close (WM_CLOSE) — same as the taskbar's
    own Close action; the app can still show its save dialog etc."""
    if not IS_WINDOWS:
        return False
    try:
        user32.PostMessageW(int(hwnd), WM_CLOSE, 0, 0)
        return True
    except Exception:
        return False
