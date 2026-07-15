"""Meridian FileBrowse shell trampoline.

This is the executable registered as the "default shell browser" (folder
open handler) by the "Make Meridian FileBrowse the default shell browser"
macro/setting. It is NOT Meridian FileBrowse itself — it's a tiny router
that Windows invokes with a folder path whenever the user opens a folder
(e.g. double-clicking one, or "This PC"), and its only job is to hand that
path to an already-running (or freshly-launched) Meridian Launcher, which
then does the actual work: bring itself to the foreground, switch to the
Explorer section, and load Meridian FileBrowse there with that path.

Build this alongside Meridian Launcher (see Build_Meridian_FileBrowse.bat)
as "Meridian FileBrowse Shell Handler.exe" and register it via the
"Make Meridian FileBrowse the default shell browser" setting, which points
Directory\\shell\\open\\command at this exe instead of explorer.exe.
"""

import os
import subprocess
import sys
import time
import urllib.parse
import urllib.request

BASE_DIR = os.path.dirname(os.path.abspath(sys.argv[0]))
LAUNCHER_EXE = os.path.join(BASE_DIR, "MeridianLauncher.exe")

_local_appdata = os.environ.get("LOCALAPPDATA") or os.path.expanduser(r"~\AppData\Local")
PORT_FILE = os.path.join(_local_appdata, "Meridian Launcher", "internal_port.txt")


def _read_port():
    try:
        with open(PORT_FILE, "r", encoding="utf-8") as f:
            return int(f.read().strip())
    except Exception:
        return None


def _try_request(path, port, timeout=1.5):
    try:
        url = f"http://127.0.0.1:{port}/internal/open-explorer?path={urllib.parse.quote(path)}"
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return resp.status == 200
    except Exception:
        return False


def main():
    if len(sys.argv) < 2:
        # No path given — just bring Meridian Launcher up/foreground.
        path = ""
    else:
        path = sys.argv[1].strip().strip('"')

    port = _read_port()
    if port and _try_request(path, port):
        return

    # Meridian Launcher isn't running (or isn't answering yet) — launch it,
    # then retry for a few seconds while it boots and starts its internal
    # server.
    try:
        if os.path.isfile(LAUNCHER_EXE):
            subprocess.Popen([LAUNCHER_EXE], cwd=BASE_DIR)
    except Exception:
        pass

    for _ in range(20):  # ~10s at 0.5s intervals
        time.sleep(0.5)
        port = _read_port()
        if port and _try_request(path, port):
            return

    # Fall back to plain Windows Explorer rather than leaving the user with
    # nothing, if Meridian Launcher never came up.
    if path:
        try:
            os.startfile(path)
        except Exception:
            pass


if __name__ == "__main__":
    main()
