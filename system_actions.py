"""System-level actions. Windows-only by design (this app targets Windows)."""

import ctypes
import os
import subprocess
import webbrowser

try:
    import psutil
except ImportError:
    psutil = None

try:
    import win32gui
    import win32con
    import win32api
    import win32process
except ImportError:
    win32gui = None
    win32con = None
    win32api = None
    win32process = None

# Processes that must never be killed by the "close all other programs" macro,
# regardless of what the user's whitelist contains. Killing these can crash
# the desktop session or take down core OS services.
PROTECTED_PROCESSES = {
    "system", "system idle process", "registry", "memory compression",
    "smss.exe", "csrss.exe", "wininit.exe", "winlogon.exe", "services.exe",
    "lsass.exe", "svchost.exe", "explorer.exe", "dwm.exe", "fontdrvhost.exe",
    "sihost.exe", "taskhostw.exe", "ctfmon.exe", "runtimebroker.exe",
    "conhost.exe", "audiodg.exe", "spoolsv.exe", "searchindexer.exe",
    "searchapp.exe", "shellexperiencehost.exe", "startmenuexperiencehost.exe",
    "textinputhost.exe", "python.exe", "pythonw.exe", "cmd.exe",
}


SW_SHOWMAXIMIZED = 3


def launch_path(path: str, args=None):
    """Launch an .exe or .bat, requesting a maximized window. Returns
    (ok, error_message).

    Windows has no way to force an arbitrary app into true borderless
    fullscreen from the outside — that's an app-specific concept apps opt
    into themselves (F11, in-app settings, etc). The closest universal
    equivalent a launcher can request is "start maximized", via the
    show_cmd/STARTUPINFO window-show hint below. It's a hint, not a
    guarantee: well-behaved apps honor it, some ignore it and remember
    their own last window size/position instead.

    os.startfile resolves file associations the same way double-clicking in
    Explorer would, which matters for .bat/.cmd: Windows can't CreateProcess
    those directly (subprocess.Popen(["x.bat"]) raises WinError 193), they
    have to be handed to cmd.exe. os.startfile does that for us.

    args: optional list of extra command-line arguments. Used for the other
    Meridian apps (CyberDeckBrowser.exe, "Meridian Game Library.exe",
    onscreenmenu.exe), which understand a --window-mode=borderless-fullscreen
    flag requesting they open in windowed (borderless) fullscreen rather
    than whatever window mode they last had saved — that request only
    works for apps we actually wrote, unlike the maximize hint above, which
    is the best that can be asked of an arbitrary third-party program.
    os.startfile can't pass arguments, so when args are given this always
    goes through subprocess.Popen instead.
    """
    if not path or not os.path.isfile(path):
        return False, "File not found."
    try:
        if args:
            ext = os.path.splitext(path)[1].lower()
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = SW_SHOWMAXIMIZED
            if ext in (".bat", ".cmd"):
                subprocess.Popen(["cmd.exe", "/c", path] + list(args), cwd=os.path.dirname(path) or None,
                                  startupinfo=startupinfo)
            else:
                subprocess.Popen([path] + list(args), cwd=os.path.dirname(path) or None, shell=False,
                                  startupinfo=startupinfo)
        elif hasattr(os, "startfile"):
            try:
                # show_cmd param requires Python 3.10+
                os.startfile(path, show_cmd=SW_SHOWMAXIMIZED)
            except TypeError:
                os.startfile(path)
        else:
            ext = os.path.splitext(path)[1].lower()
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = SW_SHOWMAXIMIZED
            if ext in (".bat", ".cmd"):
                subprocess.Popen(["cmd.exe", "/c", path], cwd=os.path.dirname(path) or None,
                                  startupinfo=startupinfo)
            else:
                subprocess.Popen([path], cwd=os.path.dirname(path) or None, shell=False,
                                  startupinfo=startupinfo)
        return True, None
    except Exception as e:
        return False, str(e)


def _run(cmd):
    try:
        subprocess.Popen(cmd)
        return True, None
    except Exception as e:
        return False, str(e)


def another_instance_running(exe_name: str) -> bool:
    """Whether a DIFFERENT process is already running this same exe name -
    excludes both our own PID and our own PARENT's PID.

    Excluding the parent matters for any compiled --onefile app: its
    PyInstaller bootloader briefly runs as its own process (sharing the
    same exe name) before extracting and exec'ing the real app as a
    child, so on every single compiled launch there are, for a moment,
    two processes alive that would both match this name - the bootloader
    (this process's parent) and this process itself. Only excluding our
    own PID (not the parent's too) means every compiled launch falsely
    concludes "another instance is already running" and exits
    immediately - this was a real bug found in onscreenmenu's own
    single-instance check; every app doing this same kind of check
    should exclude both."""
    if psutil is None:
        return False
    my_pid = os.getpid()
    my_parent_pid = os.getppid()
    exe_name = exe_name.lower()
    for proc in psutil.process_iter(["pid", "name"]):
        try:
            if proc.pid in (my_pid, my_parent_pid):
                continue
            if (proc.info.get("name") or "").lower() == exe_name:
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, Exception):
            continue
    return False


def is_process_running(exe_name: str) -> bool:
    """Case-insensitive check for whether a process with this executable
    name (e.g. 'onscreenmenu.exe') is currently running."""
    if psutil is None:
        return False
    exe_name = exe_name.lower()
    for proc in psutil.process_iter(["name"]):
        try:
            if (proc.info.get("name") or "").lower() == exe_name:
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, Exception):
            continue
    return False


def kill_process(exe_name: str):
    """Terminates every running process with this executable name
    (case-insensitive). Used by the Start menu's "Launch/Close
    onscreenmenu" toggle."""
    if psutil is None:
        return False, "psutil not available."
    exe_name = exe_name.lower()
    found = False
    try:
        for proc in psutil.process_iter(["name"]):
            try:
                if (proc.info.get("name") or "").lower() == exe_name:
                    found = True
                    proc.terminate()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        if not found:
            return True, None  # already not running - not an error
        return True, None
    except Exception as e:
        return False, str(e)


def focus_process_window(exe_name: str) -> bool:
    """Brings an already-running process's top-level window to the
    foreground, by executable name (case-insensitive). Used for
    single-instance enforcement: rather than launching a second copy of
    something that only ever makes sense as one instance (Meridian
    Explorer/FileBrowse - see main.py's launch_meridian_explorer /
    open_desktop_entry / load_explorer_box), find and focus the existing
    one instead. Returns False if no matching process/window was found,
    so the caller can fall back to actually launching it.

    Uses the same AttachThreadInput technique as Meridian Launcher's own
    Start+Select foreground combo (see main.py's _bring_to_foreground):
    plain SetForegroundWindow can silently no-op when called from a
    process that doesn't already "own" focus in some way, which is
    exactly the situation here (an unrelated app's window is likely
    what's actually focused when this gets called)."""
    if win32gui is None or win32process is None:
        return False
    exe_name = exe_name.lower()
    target_pids = set()
    if psutil is not None:
        for proc in psutil.process_iter(["pid", "name"]):
            try:
                if (proc.info.get("name") or "").lower() == exe_name:
                    target_pids.add(proc.pid)
            except (psutil.NoSuchProcess, psutil.AccessDenied, Exception):
                continue
    if not target_pids:
        return False

    found = {"hwnd": None}

    def _enum_cb(hwnd, _):
        if not win32gui.IsWindowVisible(hwnd):
            return True
        if win32gui.GetParent(hwnd) != 0:
            return True
        if not win32gui.GetWindowText(hwnd):
            return True
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        if pid in target_pids:
            found["hwnd"] = hwnd
            return False
        return True

    try:
        win32gui.EnumWindows(_enum_cb, None)
    except Exception:
        pass
    hwnd = found["hwnd"]
    if not hwnd:
        return False

    try:
        if win32gui.IsIconic(hwnd):
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        cur_thread = win32api.GetCurrentThreadId()
        fg_hwnd = win32gui.GetForegroundWindow()
        fg_thread = 0
        if fg_hwnd:
            try:
                fg_thread, _ = win32process.GetWindowThreadProcessId(fg_hwnd)
            except Exception:
                fg_thread = 0
        attached = False
        if fg_thread and fg_thread != cur_thread:
            try:
                attached = bool(ctypes.windll.user32.AttachThreadInput(fg_thread, cur_thread, True))
            except Exception:
                attached = False
        try:
            win32gui.BringWindowToTop(hwnd)
            win32gui.SetForegroundWindow(hwnd)
        finally:
            if attached:
                try:
                    ctypes.windll.user32.AttachThreadInput(fg_thread, cur_thread, False)
                except Exception:
                    pass
        return True
    except Exception:
        return False


def open_folder(path):
    """Open a folder in Windows Explorer, creating it first if it doesn't
    exist yet."""
    try:
        os.makedirs(path, exist_ok=True)
        os.startfile(path)
        return True, None
    except Exception as e:
        return False, str(e)


def open_default_browser(url: str = "https://www.google.com"):
    try:
        webbrowser.open(url)
        return True, None
    except Exception as e:
        return False, str(e)


def open_this_pc():
    return _run(["explorer.exe", "shell:MyComputerFolder"])


def open_recycle_bin():
    return _run(["explorer.exe", "shell:RecycleBinFolder"])


def delete_to_recycle_bin(path):
    """Sends a file or folder to the Recycle Bin - NOT a permanent
    delete - via the Windows Shell API (SHFileOperationW with FO_DELETE +
    FOF_ALLOWUNDO, the same mechanism Explorer's own Delete key uses).
    Used by the Desktop and System sections' Start-menu Delete option.
    Returns (ok, error)."""
    if win32gui is None:
        return False, "pywin32 not available"
    try:
        import ctypes.wintypes as wintypes

        class SHFILEOPSTRUCTW(ctypes.Structure):
            _fields_ = [
                ("hwnd", wintypes.HWND),
                ("wFunc", wintypes.UINT),
                ("pFrom", wintypes.LPCWSTR),
                ("pTo", wintypes.LPCWSTR),
                ("fFlags", ctypes.c_uint16),
                ("fAnyOperationsAborted", wintypes.BOOL),
                ("hNameMappings", ctypes.c_void_p),
                ("lpszProgressTitle", wintypes.LPCWSTR),
            ]

        FO_DELETE = 3
        FOF_ALLOWUNDO = 0x0040   # send to Recycle Bin instead of permanently deleting
        FOF_NOCONFIRMATION = 0x0010  # Meridian's own confirm prompt already asked
        FOF_SILENT = 0x0004

        # pFrom must be a double-null-terminated string (Shell API quirk),
        # even for a single path.
        pFrom = path + "\0\0"

        op = SHFILEOPSTRUCTW()
        op.hwnd = None
        op.wFunc = FO_DELETE
        op.pFrom = pFrom
        op.pTo = None
        op.fFlags = FOF_ALLOWUNDO | FOF_NOCONFIRMATION | FOF_SILENT
        op.fAnyOperationsAborted = False
        op.hNameMappings = None
        op.lpszProgressTitle = None

        result = ctypes.windll.shell32.SHFileOperationW(ctypes.byref(op))
        if result != 0:
            return False, "SHFileOperationW failed (code %d)" % result
        if op.fAnyOperationsAborted:
            return False, "Delete was cancelled"
        return True, None
    except Exception as e:
        return False, str(e)


def open_uninstall_apps():
    # ms-settings: URIs aren't regular executables — os.startfile resolves
    # the URI scheme handler the same way clicking a link to it would.
    try:
        os.startfile("ms-settings:appsfeatures")
        return True, None
    except Exception as e:
        return False, str(e)


def open_bluetooth_settings():
    try:
        os.startfile("ms-settings:bluetooth")
        return True, None
    except Exception as e:
        return False, str(e)


def open_control_panel():
    return _run(["control.exe"])


def open_task_manager():
    return _run(["taskmgr.exe"])


def open_command_prompt():
    """Opens a normal (non-elevated) Command Prompt window."""
    return _run(["cmd.exe"])


def open_powershell():
    """Opens a normal (non-elevated) Windows PowerShell window."""
    return _run(["powershell.exe"])


def open_microsoft_store():
    # ms-windows-store: is the URI scheme handler for the Store app, same
    # as clicking its tile — os.startfile resolves it like a link.
    try:
        os.startfile("ms-windows-store:")
        return True, None
    except Exception as e:
        return False, str(e)


def open_windows_update():
    try:
        os.startfile("ms-settings:windowsupdate")
        return True, None
    except Exception as e:
        return False, str(e)


def shutdown():
    return _run(["shutdown", "/s", "/t", "0"])


def restart():
    return _run(["shutdown", "/r", "/t", "0"])


def sleep():
    return _run(["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"])


def hibernate():
    return _run(["shutdown", "/h"])


def get_battery_status():
    """Returns {"percent": int, "plugged": bool} or None if there's no
    battery at all (desktop PCs), or if it can't be read."""
    if psutil is None:
        return None
    try:
        b = psutil.sensors_battery()
        if b is None:
            return None
        return {"percent": round(b.percent), "plugged": bool(b.power_plugged)}
    except Exception:
        return None


# --------------------------------------------------------------------------
# Wi-Fi (fully functional via netsh — Windows genuinely supports scripting
# this well)
# --------------------------------------------------------------------------

def _netsh(args, timeout=15):
    return subprocess.run(
        ["netsh"] + args, capture_output=True, text=True, timeout=timeout,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )


def wifi_scan():
    """Returns (ok, list_of_networks_or_error). Each network:
    {"ssid": str, "signal": int (0-100), "secured": bool, "connected": bool}
    """
    try:
        _netsh(["wlan", "show", "networks", "mode=bssid"], timeout=5)  # nudge a rescan
        result = _netsh(["wlan", "show", "networks", "mode=bssid"])
        if result.returncode != 0:
            return False, result.stderr.strip() or "netsh returned an error"

        current = _netsh(["wlan", "show", "interfaces"])
        connected_ssid = None
        for line in current.stdout.splitlines():
            line = line.strip()
            if line.lower().startswith("ssid") and ":" in line and "bssid" not in line.lower():
                connected_ssid = line.split(":", 1)[1].strip()
                break

        networks = []
        cur = None
        for raw in result.stdout.splitlines():
            line = raw.strip()
            if line.startswith("SSID") and ":" in line:
                if cur:
                    networks.append(cur)
                ssid = line.split(":", 1)[1].strip()
                cur = {"ssid": ssid, "signal": 0, "secured": True, "connected": ssid == connected_ssid}
            elif cur is not None:
                if line.lower().startswith("authentication"):
                    auth = line.split(":", 1)[1].strip().lower()
                    cur["secured"] = "open" not in auth
                elif line.lower().startswith("signal"):
                    try:
                        cur["signal"] = int(line.split(":", 1)[1].strip().replace("%", ""))
                    except ValueError:
                        pass
        if cur:
            networks.append(cur)
        # de-dupe by SSID (multiple BSSIDs per network), keep strongest signal
        best = {}
        for n in networks:
            if not n["ssid"]:
                continue
            if n["ssid"] not in best or n["signal"] > best[n["ssid"]]["signal"]:
                best[n["ssid"]] = n
        return True, sorted(best.values(), key=lambda n: -n["signal"])
    except Exception as e:
        return False, str(e)


def wifi_connect(ssid: str, password: str = ""):
    """Connects to an SSID. If a saved profile already exists, uses it
    directly; otherwise builds a WPA2-Personal (or open) profile on the fly.
    Enterprise/802.1X networks aren't supported by this simple path."""
    try:
        profiles = _netsh(["wlan", "show", "profiles"])
        has_profile = ssid.lower() in profiles.stdout.lower()

        if not has_profile:
            if password:
                xml = _wifi_profile_xml(ssid, password)
            else:
                xml = _wifi_open_profile_xml(ssid)
            tmp_path = os.path.join(os.environ.get("TEMP", "."), f"meridian_wifi_{abs(hash(ssid))}.xml")
            with open(tmp_path, "w", encoding="utf-8") as f:
                f.write(xml)
            add_result = _netsh(["wlan", "add", "profile", f"filename={tmp_path}"])
            try:
                os.remove(tmp_path)
            except OSError:
                pass
            if add_result.returncode != 0:
                return False, add_result.stdout.strip() or add_result.stderr.strip() or "Couldn't create a network profile."

        connect_result = _netsh(["wlan", "connect", f"name={ssid}", f"ssid={ssid}"])
        if connect_result.returncode != 0:
            return False, connect_result.stdout.strip() or "Couldn't connect."
        return True, None
    except Exception as e:
        return False, str(e)


def wifi_disconnect():
    try:
        result = _netsh(["wlan", "disconnect"])
        return result.returncode == 0, (None if result.returncode == 0 else result.stdout.strip())
    except Exception as e:
        return False, str(e)


def _wifi_profile_xml(ssid, password):
    return f"""<?xml version="1.0"?>
<WLANProfile xmlns="http://www.microsoft.com/networking/WLAN/profile/v1">
  <name>{ssid}</name>
  <SSIDConfig><SSID><name>{ssid}</name></SSID></SSIDConfig>
  <connectionType>ESS</connectionType>
  <connectionMode>auto</connectionMode>
  <MSM><security>
    <authEncryption>
      <authentication>WPA2PSK</authentication>
      <encryption>AES</encryption>
      <useOneX>false</useOneX>
    </authEncryption>
    <sharedKey>
      <keyType>passPhrase</keyType>
      <protected>false</protected>
      <keyMaterial>{password}</keyMaterial>
    </sharedKey>
  </security></MSM>
</WLANProfile>"""


def _wifi_open_profile_xml(ssid):
    return f"""<?xml version="1.0"?>
<WLANProfile xmlns="http://www.microsoft.com/networking/WLAN/profile/v1">
  <name>{ssid}</name>
  <SSIDConfig><SSID><name>{ssid}</name></SSID></SSIDConfig>
  <connectionType>ESS</connectionType>
  <connectionMode>auto</connectionMode>
  <MSM><security>
    <authEncryption>
      <authentication>open</authentication>
      <encryption>none</encryption>
      <useOneX>false</useOneX>
    </authEncryption>
  </security></MSM>
</WLANProfile>"""


# --------------------------------------------------------------------------
# Bluetooth (best-effort). Windows has no equivalent of netsh for Bluetooth,
# and pairing a *new* device fundamentally requires the OS-level pairing
# ceremony (PIN confirmation, etc.) — that can't be scripted headlessly.
# What we CAN do reliably: list devices Windows already knows about via PnP,
# and toggle already-paired devices on/off (the closest scriptable analogue
# to "connect"/"disconnect"). New-device pairing links out to Windows'
# native Bluetooth settings instead of pretending to support it in-app.
# --------------------------------------------------------------------------

def bluetooth_list_devices():
    """Returns (ok, list) of already-known Bluetooth devices via PowerShell
    PnP enumeration: {"id": str, "name": str, "connected": bool}."""
    try:
        ps_cmd = (
            "Get-PnpDevice -Class Bluetooth | "
            "Select-Object InstanceId,FriendlyName,Status | ConvertTo-Json"
        )
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_cmd],
            capture_output=True, text=True, timeout=15,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        if result.returncode != 0:
            return False, result.stderr.strip() or "PowerShell query failed."
        import json as _json
        raw = result.stdout.strip()
        if not raw:
            return True, []
        data = _json.loads(raw)
        if isinstance(data, dict):
            data = [data]
        devices = []
        for d in data:
            name = d.get("FriendlyName") or "Unknown device"
            devices.append({
                "id": d.get("InstanceId", ""),
                "name": name,
                "connected": str(d.get("Status", "")).lower() == "ok",
            })
        return True, devices
    except Exception as e:
        return False, str(e)


def bluetooth_set_enabled(device_id: str, enabled: bool):
    """Best-effort connect/disconnect for an already-paired device by
    enabling/disabling its PnP entry. Requires the app to be running
    elevated (as admin) — if it isn't, this will fail with an access-denied
    style error, which is surfaced to the user rather than silently no-op'd."""
    verb = "Enable-PnpDevice" if enabled else "Disable-PnpDevice"
    try:
        ps_cmd = f'{verb} -InstanceId "{device_id}" -Confirm:$false'
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_cmd],
            capture_output=True, text=True, timeout=15,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        if result.returncode != 0:
            err = result.stderr.strip() or "Couldn't change device state (try running Meridian Launcher as Administrator)."
            return False, err
        return True, None
    except Exception as e:
        return False, str(e)


def close_all_except(whitelist_names):
    """Kill every process except those named in whitelist_names (case-insensitive)
    and the always-protected core OS processes."""
    if psutil is None:
        return {"ok": False, "error": "psutil not installed", "closed": []}

    keep = {n.strip().lower() for n in whitelist_names if n.strip()}
    keep |= PROTECTED_PROCESSES

    closed = []
    my_pid = os.getpid()
    for proc in psutil.process_iter(["pid", "name"]):
        try:
            if proc.pid == my_pid:
                continue
            name = (proc.info["name"] or "").lower()
            if name in keep:
                continue
            proc.terminate()
            closed.append(name)
        except (psutil.NoSuchProcess, psutil.AccessDenied, Exception):
            continue
    return {"ok": True, "error": None, "closed": closed}


def register_netbrowse_default_browser(trampoline_exe_path):
    """Registers the Meridian NetBrowse shell trampoline (NOT Meridian
    NetBrowse.exe itself) as a capable browser for http/https/ftp links and
    .htm/.html files, current-user only, no admin. Self-contained here
    (rather than importing Meridian_NetBrowse/default_browser.py) since
    that source tree isn't guaranteed to sit next to Meridian Launcher.exe
    in a packaged install — only the compiled exes are. As with any
    Windows default-browser registration, actually becoming THE default is
    one more click in Settings > Default apps."""
    if not hasattr(os, "startfile"):  # good enough proxy for "not on Windows"
        return False, "Windows only."
    try:
        import winreg
    except ImportError:
        return False, "Windows only."

    PROGID = "MeridianNetBrowseHTML"
    APPREG = "MeridianNetBrowse"

    def _set(path, value, name=None):
        key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, path)
        try:
            winreg.SetValueEx(key, name, 0, winreg.REG_SZ, value)
        finally:
            winreg.CloseKey(key)

    try:
        cmd = f'"{trampoline_exe_path}" "%1"'
        _set(rf"Software\Classes\{PROGID}", "Meridian NetBrowse Document")
        _set(rf"Software\Classes\{PROGID}\DefaultIcon", f'"{trampoline_exe_path}",0')
        _set(rf"Software\Classes\{PROGID}\shell\open\command", cmd)

        capbase = r"Software\MeridianNetBrowse\Capabilities"
        _set(capbase, "Meridian NetBrowse", "ApplicationName")
        _set(capbase, "Routes links through Meridian Launcher's Browser section", "ApplicationDescription")
        for scheme in ("http", "https", "ftp"):
            _set(capbase + r"\URLAssociations", PROGID, scheme)
        for ext in (".htm", ".html"):
            _set(capbase + r"\FileAssociations", PROGID, ext)
        _set(r"Software\RegisteredApplications", capbase, APPREG)

        for scheme in ("http", "https"):
            try:
                _set(rf"Software\Classes\{scheme}\shell\open\command", cmd)
            except Exception:
                pass

        return True, None
    except Exception as e:
        return False, str(e)


def launch_ps1_elevated(path, args=None):
    """Run a PowerShell script elevated — a UAC prompt for just that one
    process, not the whole app — via ShellExecuteW's "runas" verb.
    Returns (ok, error_message, needs_admin_relaunch). needs_admin_relaunch
    is True when even the per-process elevation attempt failed (e.g. the
    UAC prompt was declined, or something about the environment blocks it
    outright), which is the caller's cue to offer restarting Meridian
    Launcher itself as administrator instead.
    """
    if not path or not os.path.isfile(path):
        return False, "File not found.", False
    try:
        import ctypes
        arg_str = " ".join(f'"{a}"' for a in (args or []))
        params = f'-NoProfile -ExecutionPolicy Bypass -File "{path}"' + (f" {arg_str}" if arg_str else "")
        # SW_SHOWNORMAL = 1. Return value > 32 means success; <= 32 is an
        # HINSTANCE-shaped error code (5 = access denied / UAC declined).
        result = ctypes.windll.shell32.ShellExecuteW(
            None, "runas", "powershell.exe", params, os.path.dirname(path) or None, 1
        )
        if result > 32:
            return True, None, False
        if result == 5:
            return False, "Administrator permission was declined.", True
        return False, f"Couldn't launch elevated (error code {result}).", True
    except Exception as e:
        return False, str(e), True
