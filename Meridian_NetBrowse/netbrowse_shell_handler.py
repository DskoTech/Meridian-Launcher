"""Meridian NetBrowse shell trampoline.

Registered as the default web browser by the "Make Meridian NetBrowse the
default system web browser" macro/setting. It is NOT Meridian NetBrowse
itself — it's a tiny router that Windows invokes with a URL whenever
something asks to open the default browser (a clicked link elsewhere, "%1"
from the http/https ProgId), and its only job is to hand that URL to an
already-running (or freshly-launched) Meridian Launcher, which then does
the actual work: bring itself to the foreground, switch to the Browser
section, and load Meridian NetBrowse there with that URL.

Build this alongside Meridian Launcher (see buildMeridianNetBrowse.bat) as
"Meridian NetBrowse Shell Handler.exe" and register it via the "Make
Meridian NetBrowse the default system web browser" setting, which points
the http/https ProgId's open command at this exe instead of at Meridian
NetBrowse.exe directly.
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


def _try_request(url, port, timeout=1.5):
    try:
        target = f"http://127.0.0.1:{port}/internal/open-browser?url={urllib.parse.quote(url)}"
        with urllib.request.urlopen(target, timeout=timeout) as resp:
            return resp.status == 200
    except Exception:
        return False


def main():
    url = sys.argv[1].strip().strip('"') if len(sys.argv) > 1 else ""

    port = _read_port()
    if port and _try_request(url, port):
        return

    try:
        if os.path.isfile(LAUNCHER_EXE):
            subprocess.Popen([LAUNCHER_EXE], cwd=BASE_DIR)
    except Exception:
        pass

    for _ in range(20):  # ~10s at 0.5s intervals
        time.sleep(0.5)
        port = _read_port()
        if port and _try_request(url, port):
            return

    # Meridian Launcher never came up / never answered — fall back to
    # opening the URL in whatever the system's plain default browser is,
    # rather than leaving the user with nothing.
    if url:
        try:
            import webbrowser
            webbrowser.open(url)
        except Exception:
            pass


if __name__ == "__main__":
    main()
