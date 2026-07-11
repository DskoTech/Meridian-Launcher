"""System-level actions. Windows-only by design (this app targets Windows)."""

import os
import subprocess
import webbrowser

try:
    import psutil
except ImportError:
    psutil = None

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


def launch_path(path: str):
    """Launch an .exe or .bat. Returns (ok, error_message).

    os.startfile resolves file associations the same way double-clicking in
    Explorer would, which matters for .bat/.cmd: Windows can't CreateProcess
    those directly (subprocess.Popen(["x.bat"]) raises WinError 193), they
    have to be handed to cmd.exe. os.startfile does that for us.
    """
    if not path or not os.path.isfile(path):
        return False, "File not found."
    try:
        if hasattr(os, "startfile"):
            os.startfile(path)
        else:
            ext = os.path.splitext(path)[1].lower()
            if ext in (".bat", ".cmd"):
                subprocess.Popen(["cmd.exe", "/c", path], cwd=os.path.dirname(path) or None)
            else:
                subprocess.Popen([path], cwd=os.path.dirname(path) or None, shell=False)
        return True, None
    except Exception as e:
        return False, str(e)


def _run(cmd):
    try:
        subprocess.Popen(cmd)
        return True, None
    except Exception as e:
        return False, str(e)


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


def shutdown():
    return _run(["shutdown", "/s", "/t", "0"])


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
            err = result.stderr.strip() or "Couldn't change device state (try running Meridian Game Library as Administrator)."
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
