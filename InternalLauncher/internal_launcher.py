"""Internal Launcher — Apps section entry that opens a native file/
program picker, launches whatever was chosen, and reparents that
program's own window INTO this app's own frame (real Win32 window
embedding via SetParent, not a screenshot/mirror) - so the picked
program shows up sized/positioned like any other boxed Meridian app,
with the SAME onscreenmenu controller/cursor/on-screen-keyboard support
every other window already gets automatically (see
onscreenmenu/features/foreign_focus_watcher.py - that watcher already
works against any window with no special-casing needed here).

CLOSING BEHAVIOR (as specified):
  - The embedded program exiting closes this frame too (there's nothing
    left to show).
  - This frame closing (the [X] button, or Meridian Launcher tearing
    down the box) closes the embedded program too, rather than leaving
    it running detached with nowhere shown.
  - onscreenmenu.exe no longer running closes both - this only matters
    for controller-only setups with no other pointing method, so
    embedding something with no way left to control or close it would
    otherwise be a real dead end.

HONEST CAVEAT: real window reparenting is inherently fragile - it
depends on the target program having a normal single top-level window
(not, say, a UWP/Store app using a different window-hosting model, or a
program that intentionally resists being reparented). This handles the
common case (most classic Win32 desktop programs and document viewers)
with a bounded wait-and-poll for the window to appear and a clear error
if it doesn't, rather than hanging indefinitely or crashing.
"""

import ctypes
from ctypes import wintypes
import os
import sys
import time
import subprocess
import threading
import tkinter as tk
from tkinter import filedialog, messagebox

IS_WINDOWS = sys.platform == "win32"

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from crash_logger import install_crash_logging
    install_crash_logging("InternalLauncher")
except Exception:
    pass

try:
    import psutil
except ImportError:
    psutil = None

user32 = ctypes.windll.user32 if IS_WINDOWS else None

GWL_STYLE = -16
WS_CAPTION = 0x00C00000
WS_THICKFRAME = 0x00040000
WS_CHILD = 0x40000000
WS_POPUP = 0x80000000
SWP_FRAMECHANGED = 0x0020
SWP_NOZORDER = 0x0004
SW_HIDE = 0
SW_SHOW = 5

WINDOW_FIND_TIMEOUT_SECONDS = 20
POLL_INTERVAL_SECONDS = 0.25


def _parse_box_arg():
    for arg in sys.argv[1:]:
        if arg.startswith("--box="):
            try:
                x, y, w, h = (int(v) for v in arg[len("--box="):].split(","))
                return (x, y, w, h)
            except Exception:
                return None
    return None


def _onscreenmenu_running():
    """False (meaning: treat as 'not running', close everything) as soon
    as we can positively confirm it ISN'T - if psutil is unavailable for
    any reason, defaults to True (don't tie this frame's lifetime to a
    check that can't actually be performed) rather than closing things
    that might be working fine."""
    if psutil is None:
        return True
    try:
        for proc in psutil.process_iter(["name"]):
            if (proc.info.get("name") or "").lower() == "onscreenmenu.exe":
                return True
    except Exception:
        return True
    return False


def _launch_onscreenmenu_if_not_running():
    """Starts onscreenmenu.exe (controller cursor/OSK support - see
    onscreenmenu/features/foreign_focus_watcher.py) so whatever gets
    embedded is actually controller-navigable, same as every other
    boxed Meridian app already gets. Only launches it if it isn't
    already running (same guard every other internalized launch site in
    this suite uses - see main.py's _launch_onscreenmenu). Returns True
    if onscreenmenu ends up running (whether it started it or it was
    already there), False if it couldn't be found/started at all."""
    if _onscreenmenu_running():
        return True
    own_dir = os.path.dirname(os.path.abspath(sys.executable if getattr(sys, "frozen", False) else __file__))
    exe = os.path.join(own_dir, "onscreenmenu.exe")
    if not os.path.isfile(exe):
        return False
    try:
        subprocess.Popen([exe, "--window-mode=borderless-fullscreen"], cwd=os.path.dirname(exe))
        return True
    except Exception:
        return False


def _snapshot_top_level_windows():
    """{hwnd: True} for every currently visible, titled top-level window
    on the whole system - used as a "before" baseline so a genuinely NEW
    window appearing afterward can be recognized even when it's not a
    traceable child of anything we launched (see _find_target_window's
    docstring for why that matters)."""
    snapshot = {}
    EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

    def _cb(hwnd, _lparam):
        if user32.IsWindowVisible(hwnd) and user32.GetWindowTextLengthW(hwnd) > 0:
            snapshot[hwnd] = True
        return True

    try:
        user32.EnumWindows(EnumWindowsProc(_cb), 0)
    except Exception:
        pass
    return snapshot


def _find_target_window(pid, before_snapshot, timeout=WINDOW_FIND_TIMEOUT_SECONDS):
    """Polls for the launched program's real window using TWO signals in
    parallel, since neither is reliable alone:

    1. PID ancestry (pid, or one of its own child processes - some
       launched programs are themselves just a stub that spawns the
       real app: installers, Store-app trampolines, etc). Precise when
       it works, but Windows' shell doesn't always cooperate: "start" /
       ShellExecute for many file types gets relayed through the
       ALREADY-RUNNING explorer.exe process instead of spawning a real
       child under our own cmd.exe - the actual target program ends up
       parented under that pre-existing explorer.exe, a PID we have no
       way to predict or trace to in advance, so pure ancestry search
       can time out and find nothing even though the program opened
       fine right in front of the user. This was the actual cause of
       Internal Launcher closing itself right after a program opened
       via something Explorer's shell relayed.

    2. Any currently-visible top-level window that WASN'T in
       before_snapshot at all - doesn't depend on process ancestry, so
       it still works when signal 1 can't trace the relationship. Only
       used as a fallback once signal 1 hasn't found anything for a
       moment, and only counts a window that isn't obviously our own
       process or a background system window.

    Returns an hwnd or None."""
    start_time = time.time()
    deadline = start_time + timeout
    own_pid = os.getpid()
    while time.time() < deadline:
        candidate_pids = {pid}
        if psutil is not None:
            try:
                proc = psutil.Process(pid)
                candidate_pids |= {c.pid for c in proc.children(recursive=True)}
            except Exception:
                pass

        by_pid = []
        new_windows = []
        EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

        def _cb(hwnd, _lparam):
            if not user32.IsWindowVisible(hwnd) or user32.GetWindowTextLengthW(hwnd) <= 0:
                return True
            wpid = wintypes.DWORD(0)
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(wpid))
            if wpid.value in candidate_pids:
                by_pid.append(hwnd)
                return False
            if wpid.value != own_pid and hwnd not in before_snapshot:
                new_windows.append(hwnd)
            return True

        try:
            user32.EnumWindows(EnumWindowsProc(_cb), 0)
        except Exception:
            pass

        if by_pid:
            return by_pid[0]
        # Fallback signal only once signal 1 has had a real chance (a
        # program's OWN window sometimes briefly touches other windows
        # while starting up - waiting a beat avoids grabbing one of
        # those instead of the real thing).
        if new_windows and time.time() - start_time > 1.5:
            return new_windows[0]

        time.sleep(POLL_INTERVAL_SECONDS)
    return None


class InternalLauncherApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Internal Launcher")
        self.root.configure(bg="#0b1410")

        box = _parse_box_arg()
        if box:
            x, y, w, h = box
            self.root.overrideredirect(True)
            self.root.geometry(f"{w}x{h}+{x}+{y}")
        else:
            self.root.geometry("1000x700")

        self.status_label = tk.Label(
            self.root, text="Pick a file or program to open\u2026",
            bg="#0b1410", fg="#7CFFB2", font=("Segoe UI", 13),
        )
        self.status_label.pack(expand=True)

        self.child_pid = None
        self.child_hwnd = None
        self._closing = False
        # Only enforce "close if onscreenmenu stops" for someone who
        # actually had it running when this started - most people don't
        # run onscreenmenu.exe at all unless they specifically need
        # controller support, so treating "never was running" the same
        # as "was running, then stopped" made this close itself within
        # about a second of starting for nearly everyone, including
        # while the file picker was still open (a real bug, not the
        # intended "no way left to control this" safety net at all).
        self._onscreenmenu_was_running = _onscreenmenu_running()
        # True only once _embed() actually launches onscreenmenu itself
        # (see there) - distinguishes "we started this, we should close
        # it too" from "someone already had it running for other
        # reasons, leave it alone when we're done".
        self._launched_onscreenmenu_ourselves = False

        self.root.protocol("WM_DELETE_WINDOW", self._on_close_request)
        self.root.after(200, self._pick_and_launch)
        self.root.after(1000, self._watchdog_tick)

    def _pick_and_launch(self):
        path = filedialog.askopenfilename(
            title="Open a file or program",
            filetypes=[("All files", "*.*"), ("Programs", "*.exe")],
        )
        if not path:
            self.root.destroy()
            return
        before_snapshot = _snapshot_top_level_windows()
        try:
            proc = subprocess.Popen(["cmd", "/c", "start", "", path], shell=False)
        except Exception as e:
            messagebox.showerror("Internal Launcher", f"Couldn't open that:\n{e}")
            self.root.destroy()
            return
        self.status_label.config(text=f"Opening\u2026\n{os.path.basename(path)}")
        # "start" itself exits almost immediately once it's launched the
        # real program - the real target's own pid is often NOT a child
        # of this cmd.exe at all (Windows frequently relays ShellExecute-
        # style launches through the already-running explorer.exe shell
        # process instead) - see _find_target_window's docstring for the
        # full explanation and the two-signal search this uses to work
        # around it.
        threading.Thread(target=self._wait_for_window, args=(proc.pid, before_snapshot), daemon=True).start()

    def _wait_for_window(self, launch_pid, before_snapshot):
        hwnd = _find_target_window(launch_pid, before_snapshot)
        self.root.after(0, self._on_window_found, hwnd)

    def _on_window_found(self, hwnd):
        if self._closing:
            return
        if not hwnd:
            messagebox.showerror(
                "Internal Launcher",
                "Couldn't find a window for that program within 20 seconds - "
                "it may not have a normal window to embed (some Store apps, "
                "background-only tools, or slow-starting installers behave this way).",
            )
            self.root.destroy()
            return
        self.child_hwnd = hwnd
        wpid = wintypes.DWORD(0)
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(wpid))
        self.child_pid = wpid.value
        self._embed(hwnd)

    def _embed(self, hwnd):
        try:
            # Win32 style flags are a 32-bit UNSIGNED bitmask, but
            # several of them - WS_POPUP in particular - have bit 31 set
            # (WS_POPUP = 0x80000000). Python's ~ operator is infinite-
            # precision, not C's 32-bit wraparound: ~0x80000000 in Python
            # is -2147483649, not the 0x7FFFFFFF a C compiler would give
            # you, and that corrupted mask produces a combined style
            # value outside the 32-bit LONG range SetWindowLongW expects
            # - ctypes rejects that with OverflowError instead of
            # silently doing the wrong thing, which is what was actually
            # crashing this step. Masking every NOT down to 32 bits
            # keeps the arithmetic correct, and converting the final
            # result to signed two's complement before the call matches
            # what SetWindowLongW's LONG parameter actually expects.
            def _not32(mask):
                return (~mask) & 0xFFFFFFFF

            style = user32.GetWindowLongW(hwnd, GWL_STYLE) & 0xFFFFFFFF
            style = (style & _not32(WS_CAPTION) & _not32(WS_THICKFRAME) & _not32(WS_POPUP)) | WS_CHILD
            if style & 0x80000000:
                style -= 0x100000000  # back to signed 32-bit for the ctypes call
            user32.SetWindowLongW(hwnd, GWL_STYLE, style)

            host_hwnd = self.root.winfo_id()
            user32.SetParent(hwnd, host_hwnd)

            w = self.root.winfo_width()
            h = self.root.winfo_height()
            user32.SetWindowPos(hwnd, 0, 0, 0, w, h, SWP_FRAMECHANGED | SWP_NOZORDER)
            user32.ShowWindow(hwnd, SW_SHOW)
            self.status_label.pack_forget()

            self.root.bind("<Configure>", self._on_resize)
            self.root.after(250, self._enforce_bounds_tick)

            if not self._onscreenmenu_was_running:
                if _launch_onscreenmenu_if_not_running():
                    self._launched_onscreenmenu_ourselves = True
                    # Fold into the existing watchdog check below (see
                    # _watchdog_tick) - it already closes this frame when
                    # something it's tracking as "was running" stops
                    # running, which is exactly the behavior wanted here
                    # too, just for an onscreenmenu WE started instead of
                    # one that predates us.
                    self._onscreenmenu_was_running = True
        except Exception as e:
            messagebox.showerror("Internal Launcher", f"Couldn't embed that window:\n{e}")
            self.root.destroy()

    def _on_resize(self, _event):
        if self.child_hwnd:
            try:
                w = self.root.winfo_width()
                h = self.root.winfo_height()
                user32.SetWindowPos(self.child_hwnd, 0, 0, 0, w, h, SWP_NOZORDER)
            except Exception:
                pass

    def _enforce_bounds_tick(self):
        """Keeps the embedded window pinned to (0, 0, frame_width,
        frame_height) continuously, not just in reaction to OUR OWN
        window resizing (see _on_resize) - the embedded program is a
        real, independent Win32 app and nothing stops IT from calling
        its own SetWindowPos, maximizing itself, or otherwise resizing
        on its own initiative. Windows clips a child window's rendering
        to the area that overlaps its parent, but that's a drawing-time
        clip, not a hard constraint on the window's actual geometry - an
        oversized child can still exist off past the frame's edges,
        which shows up as odd behavior the moment this frame itself
        moves or resizes (suddenly-visible content that was there the
        whole time, just not being drawn). Reapplying every tick is
        simple and cheap - SetWindowPos with unchanged values is a
        lightweight no-op internally - rather than only correcting after
        first detecting an actual drift."""
        if self._closing or not self.child_hwnd:
            return
        try:
            w = self.root.winfo_width()
            h = self.root.winfo_height()
            user32.SetWindowPos(self.child_hwnd, 0, 0, 0, w, h, SWP_NOZORDER)
        except Exception:
            pass
        self.root.after(250, self._enforce_bounds_tick)

    def _watchdog_tick(self):
        if self._closing:
            return
        should_close = False
        if self.child_pid is not None and psutil is not None:
            try:
                if not psutil.Process(self.child_pid).is_running():
                    should_close = True
            except Exception:
                should_close = True
        if self._onscreenmenu_was_running and not _onscreenmenu_running():
            should_close = True
        if should_close:
            self._on_close_request()
            return
        self.root.after(1000, self._watchdog_tick)

    def _on_close_request(self):
        if self._closing:
            return
        self._closing = True
        if self.child_pid is not None and psutil is not None:
            try:
                proc = psutil.Process(self.child_pid)
                proc.terminate()
            except Exception:
                pass
        if self._launched_onscreenmenu_ourselves and psutil is not None:
            try:
                for proc in psutil.process_iter(["name"]):
                    if (proc.info.get("name") or "").lower() == "onscreenmenu.exe":
                        proc.terminate()
            except Exception:
                pass
        try:
            self.root.destroy()
        except Exception:
            pass

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    if not IS_WINDOWS:
        sys.exit("Internal Launcher is Windows-only.")
    InternalLauncherApp().run()
