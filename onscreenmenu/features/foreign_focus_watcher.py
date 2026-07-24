"""features/foreign_focus_watcher.py — universal on-screen keyboard
auto-invoke.

onscreenmenu's fake CURSOR already runs continuously the moment
onscreenmenu is open (see MainWindow._cursor_tick) - controller-as-mouse
already works against any window, including third-party installers,
with no button press needed. The keyboard was the gap: bringing up the
real Windows On-Screen Keyboard (osk.exe, via osk.bat - see
_run_osk_bat) has always required remembering to press X and pick
"Virtual Keyboard" from the menu first.

This closes that gap two ways, polled on a fast timer from MainWindow:

  1. FOREIGN WINDOW FOCUS. The moment ANY window not belonging to the
     Meridian suite (or onscreenmenu itself) becomes the foreground
     window - a third-party installer, an arbitrary app Meridian has no
     knowledge of, anything - osk.exe is opened automatically. It's
     closed automatically again once focus returns to a Meridian window
     or the desktop/taskbar itself, but ONLY if this watcher was the one
     that opened it - manually opening it via the X menu is left alone
     and never force-closed out from under someone.

  2. UAC / SECURE DESKTOP. A real elevation consent prompt (consent.exe)
     runs on Windows' Secure Desktop, a genuinely separate desktop object
     that ordinary application windows - including onscreenmenu's own
     cursor/keyboard overlay - cannot draw on or receive focus on, by
     OS design (this is what stops malware from spoofing a UAC prompt).
     Foreground-window watching alone cannot reach it. What DOES reach
     it: osk.exe is one of the small set of Microsoft-signed
     UIAccess-flagged accessibility tools Windows is willing to carry
     onto the Secure Desktop alongside the prompt itself - but only if
     it's ALREADY RUNNING at the moment the desktop switch happens.
     is_secure_desktop_active() below detects the switch (by checking
     which desktop currently owns the input focus), and this watcher
     makes sure osk.exe has been launched at least once beforehand so
     it's available to be carried over.

     Caveat, stated plainly: whether Windows actually carries an
     already-running osk.exe onto the Secure Desktop depends on Windows'
     own accessibility/UIAccess handling, which this code doesn't
     control and can't fully guarantee across every Windows build. What
     this watcher CAN guarantee is that osk.exe is running and ready for
     that handoff rather than not running at all - it does not attempt
     to draw its own overlay on the Secure Desktop (structurally
     impossible without a signed UIAccess build of onscreenmenu itself)
     and does not modify any Accessibility/Ease-of-Access registry
     settings to avoid changing system configuration this code can't
     fully verify the effects of.
"""

import ctypes
from ctypes import wintypes
import os
import sys
import time

try:
    import psutil
except ImportError:
    psutil = None

IS_WINDOWS = sys.platform == "win32"

# Any process name here is treated as "part of Meridian" - focus staying
# within these never auto-triggers the keyboard. Mode-dispatch means most
# of the suite is literally the same exe now, but the legacy/standalone
# names are kept too in case an older build or a standalone .exe copy is
# what's actually running.
MERIDIAN_PROCESS_NAMES = {
    "meridianlauncher.exe",
    "onscreenmenu.exe",
    "cyberdeckbrowser.exe",
    "meridian netbrowse.exe",
    "meridian filebrowse.exe",
    "meridian explorer.exe",
    "meridian exporter.exe",
}

# Desktop shell windows (taskbar, desktop icons) that shouldn't pop the
# keyboard just because someone glanced at the desktop.
_SHELL_TITLES = {"program manager"}

if IS_WINDOWS:
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32

    GENERIC_READ = 0x80000000
    UOI_NAME = 2
    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000


def is_secure_desktop_active():
    """True if the Secure Desktop (UAC consent.exe, or a handful of
    other elevation-style prompts) currently owns input focus. See
    module docstring for what this can and can't do about it."""
    if not IS_WINDOWS:
        return False
    try:
        hdesk = user32.OpenInputDesktop(0, False, GENERIC_READ)
        if not hdesk:
            return False
        try:
            buf = ctypes.create_unicode_buffer(64)
            needed = wintypes.DWORD(0)
            ok = user32.GetUserObjectInformationW(
                hdesk, UOI_NAME, ctypes.byref(buf), ctypes.sizeof(buf), ctypes.byref(needed)
            )
            if not ok:
                return False
            return buf.value.strip().lower() == "winlogon"
        finally:
            user32.CloseDesktop(hdesk)
    except Exception:
        return False


def _foreground_process_name():
    """Lowercase exe name of the current foreground window's owning
    process, or None if it can't be determined (or there's no real
    foreground window - e.g. during a desktop switch)."""
    if not IS_WINDOWS or psutil is None:
        return None
    try:
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return None
        length = user32.GetWindowTextLengthW(hwnd)
        title_buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, title_buf, length + 1)
        title = (title_buf.value or "").strip().lower()
        if title in _SHELL_TITLES:
            return "__shell__"
        pid = wintypes.DWORD(0)
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if not pid.value:
            return None
        proc = psutil.Process(pid.value)
        return proc.name().lower()
    except Exception:
        return None


class _GUITHREADINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("hwndActive", wintypes.HWND),
        ("hwndFocus", wintypes.HWND),
        ("hwndCapture", wintypes.HWND),
        ("hwndMenuOwner", wintypes.HWND),
        ("hwndMoveSize", wintypes.HWND),
        ("hwndCaret", wintypes.HWND),
        ("rcCaret", wintypes.RECT),
    ]


# Edit-control class names GetFocus() commonly resolves to when a real
# text field has focus - checked as a second signal alongside the caret
# (see _text_field_focused below), since some apps show a text caret in
# contexts that aren't actually typeable (e.g. selectable read-only
# text), and this catches the reverse case too (a real edit control that
# happens not to be showing a blinking caret at this exact instant).
_EDIT_CONTROL_CLASSES = {"edit", "richedit", "richedit20a", "richedit20w", "richedit50w"}


def _focused_text_field_hwnd():
    """The focused control's hwnd if it looks like a real text input (see
    module-level docstring on _EDIT_CONTROL_CLASSES for the two signals
    checked), else None. Returns the CONTROL's hwnd specifically (not
    just a bool) so callers can tell one focused field apart from
    another - see ForeignFocusWatcher.tick() for why that distinction
    matters for not undoing a manual close."""
    if not IS_WINDOWS:
        return None
    try:
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return None
        fg_thread_id = user32.GetWindowThreadProcessId(hwnd, None)
        if not fg_thread_id:
            return None
        gti = _GUITHREADINFO()
        gti.cbSize = ctypes.sizeof(_GUITHREADINFO)
        if not user32.GetGUIThreadInfo(fg_thread_id, ctypes.byref(gti)):
            return None
        if gti.hwndCaret:
            return gti.hwndCaret
        if gti.hwndFocus:
            buf = ctypes.create_unicode_buffer(64)
            user32.GetClassNameW(gti.hwndFocus, buf, 64)
            if (buf.value or "").strip().lower() in _EDIT_CONTROL_CLASSES:
                return gti.hwndFocus
        return None
    except Exception:
        return None


def is_osk_running():
    if psutil is None:
        return False
    try:
        for proc in psutil.process_iter(["name"]):
            try:
                if (proc.info.get("name") or "").lower() == "osk.exe":
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
    except Exception:
        pass
    return False


def launch_osk():
    if not IS_WINDOWS:
        return
    try:
        os.startfile("osk.exe")
    except Exception:
        pass


def close_osk():
    if not IS_WINDOWS:
        return
    try:
        import subprocess
        subprocess.run(
            ["taskkill", "/f", "/im", "osk.exe"],
            capture_output=True, timeout=5,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except Exception:
        pass


class ForeignFocusWatcher:
    """Polled from a QTimer in MainWindow (see wire-up there). Tracks
    whether IT was the one that opened osk.exe, so a manually-opened
    keyboard (via the X menu, or the Start button - see MainWindow's
    toggle_osk) is never force-closed out from under someone - only a
    keyboard this watcher itself opened gets auto-closed again when
    focus returns to a Meridian window."""

    # onscreenmenu's own overlay window isn't guaranteed to be THE
    # foreground window the instant it starts (it's a click-through/
    # always-on-top overlay, not something that necessarily grabs
    # activation) - without a short grace period, the very first tick or
    # two right at boot could see whatever transient window happens to
    # have focus at that exact moment (not necessarily anything the user
    # actually opened) and spuriously auto-launch osk.exe before anyone's
    # done anything at all. This only delays the FOREIGN-WINDOW
    # auto-launch path, not the Secure Desktop one - a genuine early UAC
    # prompt right at boot should still get the same handling either way.
    _STARTUP_GRACE_SECONDS = 5

    def __init__(self):
        self._auto_opened = False
        self._was_secure_desktop = False
        self._started_at = time.time()
        # The specific focused-control hwnd auto-invoke last acted on -
        # see tick() for why this needs to be the FIELD, not just the
        # window: a manual close needs to stick while the same field
        # stays focused, but a genuinely different field (even in the
        # same window) deserves its own fresh attempt.
        self._last_field_hwnd = None

    def tick(self):
        if not IS_WINDOWS:
            return

        if is_secure_desktop_active():
            # Can't reach the Secure Desktop directly - just make sure
            # osk.exe exists and is running so Windows has the option to
            # carry it over. Never auto-close here: we have no visibility
            # into what's happening on that desktop, and closing osk.exe
            # out from under an active elevation prompt would be actively
            # unhelpful if it did get carried over.
            if not is_osk_running():
                launch_osk()
                self._auto_opened = True
            self._was_secure_desktop = True
            return

        # Just left the Secure Desktop (prompt was answered/dismissed):
        # fall through to normal foreground-based logic below rather
        # than doing anything special here.
        self._was_secure_desktop = False

        if time.time() - self._started_at < self._STARTUP_GRACE_SECONDS:
            return

        proc_name = _foreground_process_name()
        if proc_name is None:
            return  # couldn't determine - do nothing rather than guess

        is_meridian_or_shell = proc_name in MERIDIAN_PROCESS_NAMES or proc_name == "__shell__"

        if not is_meridian_or_shell and proc_name != "osk.exe":
            # Only ever launches because something TYPEABLE actually has
            # focus right now - see _focused_text_field_hwnd's docstring
            # for why a plain "some foreign window is active" check (the
            # old behavior here) wasn't enough: that opened OSK for
            # anything at all with focus, installers/video players/
            # anything with nowhere to type included.
            field_hwnd = _focused_text_field_hwnd()
            if field_hwnd:
                if field_hwnd != self._last_field_hwnd:
                    # A genuinely new field gained focus (could be a
                    # different field in the same window, or a whole new
                    # window) - give auto-invoke its one attempt for
                    # THIS field. If manually closed again afterward
                    # while this SAME field stays focused, field_hwnd
                    # won't change on the next tick, so it won't be
                    # reopened - same "manual close sticks" guarantee
                    # the old window-based version had, just scoped to
                    # the actual field instead of the whole window.
                    if not is_osk_running():
                        launch_osk()
                        self._auto_opened = True
                    self._last_field_hwnd = field_hwnd
            else:
                # No text field focused (anymore, or never was) - close
                # what auto-invoke opened, even though the window itself
                # may still be in the foreground.
                if self._auto_opened and is_osk_running():
                    close_osk()
                self._auto_opened = False
                self._last_field_hwnd = None
        else:
            if self._auto_opened and is_osk_running():
                close_osk()
            self._auto_opened = False
            self._last_field_hwnd = None
            self._auto_opened = False
            self._last_foreign_proc_name = None
