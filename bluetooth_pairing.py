"""bluetooth_pairing.py — real scan-and-pair for the "Wi-Fi & Bluetooth"
plug-on (System section), not just on/off toggling of devices Windows
already knows about.

Two problems with the old system_actions.bluetooth_list_devices():

  1. Names: `Get-PnpDevice -Class Bluetooth` mostly enumerates the
     Bluetooth STACK's own PnP nodes (radios, "Bluetooth Device
     (Personal Area Network)", generic enumerator entries) rather than
     the actual paired peripherals, and even when a real device shows up
     there its FriendlyName is often a generic driver-assigned string,
     not the name you paired it under. The name Windows actually shows
     you in Settings > Bluetooth comes from the pairing database instead
     - HKLM\\SYSTEM\\CurrentControlSet\\Services\\BTHPORT\\Parameters\\
     Devices\\<12-hex-char MAC>, a "Name" binary value written at pair
     time. list_paired_devices() below reads that directly (read-only;
     no risk to anything) and cross-references Get-PnpDevice only for a
     best-effort connected/disconnected status per device.

  2. Pairing a NEW device: not present at all before - the old code
     explicitly punted to native Windows Bluetooth settings. Real
     pairing requires the WinRT Windows.Devices.Enumeration /
     Windows.Devices.Bluetooth APIs, which have no netsh-style CLI and
     no pywin32 wrapper. PowerShell can load WinRT types directly via
     the `[Namespace.Type,Assembly,ContentType=WindowsRuntime]` syntax
     without installing anything extra, so scan_new_devices() and
     pair_device() below shell out to small embedded PowerShell scripts
     that do that. WinRT calls are async-only; PowerShell has no native
     await, so both scripts include the standard
     IAsyncOperation<T>.AsTask()-via-reflection helper to block on them.

     pair_device() auto-accepts "ConfirmOnly" and "DisplayPin" pairing
     (how the large majority of controllers/headsets pair - Windows
     shows/asks for nothing else for those), which covers the stated
     goal (pairing a controller or headset from the couch) without
     needing to relay a PIN-entry ceremony through the UI. A device that
     asks for anything else (typically physical keyboards, which want a
     PIN typed ON the device, not here) reports a clear error instead of
     hanging.

     Caveat: this is a genuinely less common corner of Windows to
     automate, and I haven't been able to test it end-to-end. If it
     doesn't accept a specific device on your machine, the fallback is
     the same "open native Bluetooth settings" this launcher already
     has (open_bluetooth_settings() in system_actions.py).
"""

import subprocess
import sys

IS_WINDOWS = sys.platform == "win32"

_PS_TIMEOUT_SCAN = 20
_PS_TIMEOUT_PAIR = 25

_CREATE_NO_WINDOW = 0x08000000

_AWAIT_HELPER = r"""
Add-Type -AssemblyName System.Runtime.WindowsRuntime
$__asTaskGeneric = ([System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {
  $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1'
})[0]
function Await-WinRT($WinRtTask, $ResultType) {
  $asTask = $__asTaskGeneric.MakeGenericMethod($ResultType)
  $netTask = $asTask.Invoke($null, @($WinRtTask))
  $netTask.Wait(-1) | Out-Null
  return $netTask.Result
}
"""

_SCAN_SCRIPT = _AWAIT_HELPER + r"""
[Windows.Devices.Enumeration.DeviceInformation,Windows.Devices.Enumeration,ContentType=WindowsRuntime] | Out-Null
[Windows.Devices.Bluetooth.BluetoothDevice,Windows.Devices.Bluetooth,ContentType=WindowsRuntime] | Out-Null
[Windows.Devices.Bluetooth.BluetoothLEDevice,Windows.Devices.Bluetooth,ContentType=WindowsRuntime] | Out-Null

$out = @()
try {
  $classicSelector = [Windows.Devices.Bluetooth.BluetoothDevice]::GetDeviceSelectorFromPairingState($false)
  $classic = Await-WinRT ([Windows.Devices.Enumeration.DeviceInformation]::FindAllAsync($classicSelector)) ([Windows.Devices.Enumeration.DeviceInformationCollection])
  foreach ($d in $classic) { if ($d.Name) { $out += [PSCustomObject]@{ id=$d.Id; name=$d.Name; kind="classic" } } }
} catch {}
try {
  $leSelector = [Windows.Devices.Bluetooth.BluetoothLEDevice]::GetDeviceSelectorFromPairingState($false)
  $le = Await-WinRT ([Windows.Devices.Enumeration.DeviceInformation]::FindAllAsync($leSelector)) ([Windows.Devices.Enumeration.DeviceInformationCollection])
  foreach ($d in $le) { if ($d.Name) { $out += [PSCustomObject]@{ id=$d.Id; name=$d.Name; kind="le" } } }
} catch {}
$out | ConvertTo-Json -Compress
"""

_PAIR_SCRIPT = _AWAIT_HELPER + r"""
param([string]$DeviceId)
[Windows.Devices.Enumeration.DeviceInformation,Windows.Devices.Enumeration,ContentType=WindowsRuntime] | Out-Null
[Windows.Devices.Enumeration.DevicePairingKinds,Windows.Devices.Enumeration,ContentType=WindowsRuntime] | Out-Null

try {
  $di = Await-WinRT ([Windows.Devices.Enumeration.DeviceInformation]::CreateFromIdAsync($DeviceId)) ([Windows.Devices.Enumeration.DeviceInformation])
  $custom = $di.Pairing.Custom
  $acceptKinds = [Windows.Devices.Enumeration.DevicePairingKinds]::ConfirmOnly -bor [Windows.Devices.Enumeration.DevicePairingKinds]::DisplayPin
  $sub = Register-ObjectEvent -InputObject $custom -EventName PairingRequested -Action {
    try { $EventArgs.Accept() } catch {}
  }
  try {
    $result = Await-WinRT ($custom.PairAsync($acceptKinds)) ([Windows.Devices.Enumeration.DevicePairingResult])
    [PSCustomObject]@{ ok = ($result.Status -eq 0); status = $result.Status.ToString() } | ConvertTo-Json -Compress
  } finally {
    Unregister-Event -SourceIdentifier $sub.Name -ErrorAction SilentlyContinue
  }
} catch {
  [PSCustomObject]@{ ok = $false; status = "error"; error = $_.Exception.Message } | ConvertTo-Json -Compress
}
"""


def _run_ps(script, args=None, timeout=20):
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script] + (args or []),
            capture_output=True, text=True, timeout=timeout,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        return result
    except subprocess.TimeoutExpired:
        return None
    except Exception:
        return None


def list_paired_devices():
    """[{"id"/mac, "name", "connected"}] for devices Windows has already
    paired, with names read straight from the pairing database (see
    module docstring) instead of PnP's often-generic FriendlyName."""
    if not IS_WINDOWS:
        return []
    try:
        import winreg
    except ImportError:
        return []

    devices = []
    try:
        key = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SYSTEM\CurrentControlSet\Services\BTHPORT\Parameters\Devices",
        )
    except OSError:
        return []

    try:
        i = 0
        while True:
            try:
                mac = winreg.EnumKey(key, i)
            except OSError:
                break
            i += 1
            try:
                sub = winreg.OpenKey(key, mac)
            except OSError:
                continue
            try:
                try:
                    raw_name, _ = winreg.QueryValueEx(sub, "Name")
                    name = bytes(raw_name).split(b"\x00")[0].decode("utf-8", errors="replace").strip()
                except OSError:
                    name = None
                connected = False
                try:
                    flags, _ = winreg.QueryValueEx(sub, "ConnectionFlags")
                    connected = bool(flags)
                except OSError:
                    pass
                if name:
                    devices.append({"id": mac, "name": name, "connected": connected})
            finally:
                winreg.CloseKey(sub)
    finally:
        winreg.CloseKey(key)
    return devices


def scan_new_devices():
    """Runs one WinRT discovery pass (~a few seconds) for Bluetooth
    devices NOT already paired. Returns {"ok", "devices", "error"}."""
    if not IS_WINDOWS:
        return {"ok": False, "devices": [], "error": "Windows only."}
    result = _run_ps(_SCAN_SCRIPT, timeout=_PS_TIMEOUT_SCAN)
    if result is None:
        return {"ok": False, "devices": [], "error": "Scan timed out."}
    if result.returncode != 0:
        return {"ok": False, "devices": [], "error": result.stderr.strip() or "Scan failed."}
    raw = (result.stdout or "").strip()
    if not raw:
        return {"ok": True, "devices": [], "error": None}
    try:
        import json
        data = json.loads(raw)
        if isinstance(data, dict):
            data = [data]
        return {"ok": True, "devices": data, "error": None}
    except Exception as e:
        return {"ok": False, "devices": [], "error": f"Couldn't parse scan results: {e}"}


def pair_device(device_id):
    """Pairs a device found by scan_new_devices(). Auto-accepts
    ConfirmOnly/DisplayPin pairing kinds (covers the large majority of
    controllers/headsets); anything else reports an error rather than
    hanging. Returns {"ok", "error"}."""
    if not IS_WINDOWS:
        return {"ok": False, "error": "Windows only."}
    result = _run_ps(_PAIR_SCRIPT, args=["-DeviceId", device_id], timeout=_PS_TIMEOUT_PAIR)
    if result is None:
        return {"ok": False, "error": "Pairing timed out. Check for a Windows pairing prompt, or try native Bluetooth settings."}
    raw = (result.stdout or "").strip()
    if not raw:
        return {"ok": False, "error": result.stderr.strip() or "Pairing failed with no further detail."}
    try:
        import json
        data = json.loads(raw)
        return {"ok": bool(data.get("ok")), "error": data.get("error") or (None if data.get("ok") else f"Pairing status: {data.get('status')}")}
    except Exception as e:
        return {"ok": False, "error": f"Couldn't parse pairing result: {e}"}
