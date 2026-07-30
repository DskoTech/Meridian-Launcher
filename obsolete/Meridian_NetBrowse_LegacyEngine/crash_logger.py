"""
Meridian suite crash logger.

Installs a global handler that catches unhandled Python exceptions
(including ones raised in background threads) and writes a timestamped,
detailed log file to the app's own folder, instead of the app just
silently vanishing or dumping a traceback to a console window nobody's
watching.

Usage (as early as possible in each app's own main.py / launcher.py):

    from crash_logger import install_crash_logging
    install_crash_logging("Meridian Launcher")

Every crash gets its own file: crash_log_<AppName>_<timestamp>.txt, in the
same folder as the running exe/script (not %TEMP% or anywhere else, so
they're easy to find and hand back). If a lot of these pile up, it's fine
to just delete them - nothing reads them back in.

IMPORTANT LIMITATION: this can only catch actual Python exceptions. A
genuine native crash (a Windows access violation / segfault from a bad
ctypes call, the historical GameInput vtable issue in particular) usually
—but not always— surfaces as a normal Python OSError that this WILL catch
and log; but a severe enough memory corruption can still kill the whole
process before any Python code, including this handler, gets to run. If
the app vanishes with no crash log at all, that's the signature of that
harder case, not a bug in this logger.
"""

import datetime
import os
import platform
import sys
import threading
import traceback


def _base_dir():
    """Frozen-aware: the real folder the exe/script lives in, matching
    the pattern every app in this suite already uses for its own
    BASE_DIR — Path(__file__) alone resolves into PyInstaller's temp
    extraction folder when compiled, not the real install folder."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


def _write_crash_log(app_name, exc_type, exc_value, exc_tb, thread_name=None):
    try:
        base = _base_dir()
        stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_app = "".join(c if c.isalnum() else "_" for c in (app_name or "Meridian"))
        path = os.path.join(base, f"crash_log_{safe_app}_{stamp}.txt")
        lines = [
            f"Meridian crash log — {app_name or '(unknown app)'}",
            "=" * 70,
            f"Time       : {datetime.datetime.now().isoformat()}",
            f"Thread     : {thread_name or 'main'}",
            f"Python     : {platform.python_version()} ({platform.architecture()[0]})",
            f"Platform   : {platform.platform()}",
            f"Frozen     : {getattr(sys, 'frozen', False)}",
            f"Executable : {sys.executable}",
            f"Argv       : {sys.argv}",
            "",
            "Traceback:",
            "-" * 70,
            "".join(traceback.format_exception(exc_type, exc_value, exc_tb)),
        ]
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        # Also print it, in case a console is attached — costs nothing,
        # helps if you're already watching one when it happens.
        print(f"\n[Meridian crash logger] wrote {path}\n", file=sys.stderr)
    except Exception:
        # If the logger itself fails, don't let that mask/replace the
        # original crash with a new one — just give up quietly.
        pass


def install_crash_logging(app_name=None):
    """Call once, as early as possible in an app's own entry point."""

    def _excepthook(exc_type, exc_value, exc_tb):
        _write_crash_log(app_name, exc_type, exc_value, exc_tb)
        # Still call the default hook too, so a console (if any) shows the
        # normal traceback exactly like it would have without this.
        sys.__excepthook__(exc_type, exc_value, exc_tb)

    sys.excepthook = _excepthook

    # Python 3.8+: background-thread exceptions don't go through
    # sys.excepthook at all by default, they'd just print to stderr and
    # otherwise vanish — this catches those too.
    if hasattr(threading, "excepthook"):
        def _thread_excepthook(args):
            _write_crash_log(
                app_name, args.exc_type, args.exc_value, args.exc_traceback,
                thread_name=(args.thread.name if args.thread else None),
            )
            threading.__excepthook__(args)

        threading.excepthook = _thread_excepthook
