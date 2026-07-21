"""audio_devices.py — enumerate and switch the Windows default audio
playback (output) device, for Settings/System > Audio Output.

Built on pycaw, which already wraps the two COM pieces this needs:
  - IMMDeviceEnumerator (AudioUtilities.GetAllDevices/GetSpeakers) to
    list render endpoints and see which one is currently default.
  - IPolicyConfig (undocumented but stable since Vista, and how every
    other default-device switcher — NirCmd, AudioDeviceCmdlets,
    SoundSwitch — does this too) to actually SET the default, which
    neither the public Core Audio APIs nor pycaw's own AudioUtilities
    expose a supported way to do.

Sets all three roles (console, multimedia, communications) to the same
device on switch, matching what Windows' own Sound Settings page does
when you pick an output from the dropdown, so this doesn't leave calls
routed to a different device than everything else.
"""

import sys

IS_WINDOWS = sys.platform == "win32"

# Deliberately NOT a bare `if IS_WINDOWS: import pycaw...` - that crashed
# the whole app at startup (ModuleNotFoundError inside main.py's own
# import chain) on any build where pycaw/comtypes weren't actually
# bundled into the frozen exe, even though this is meant to be an
# optional, best-effort feature like SDL3/ffmpeg elsewhere in the suite.
# See the PyInstaller .spec's hiddenimports for the actual fix to WHY
# pycaw wasn't bundled (its imports are dynamic enough that PyInstaller's
# static analysis misses them without help) - this try/except is the
# safety net for that, not a substitute for it: a machine that's missing
# it should get "Audio Output switching unavailable" in the UI, never a
# crash.
_PYCAW_IMPORT_ERROR = None
if IS_WINDOWS:
    try:
        import comtypes
        from pycaw.utils import AudioUtilities
        from pycaw.api.policyconfig import IPolicyConfig
        from pycaw.constants import CLSID_CPolicyConfigClient, ERole, AudioDeviceState
    except ImportError as e:
        _PYCAW_IMPORT_ERROR = str(e)
else:
    _PYCAW_IMPORT_ERROR = "Windows only."


def _friendly_name(device):
    name = device.FriendlyName
    return name if name else device.id


def import_error():
    """None if pycaw/comtypes imported fine, else a human-readable reason
    - for callers (the Api wrapper in main.py, display_audio_server.py)
    to surface instead of a misleading empty "no devices found" list."""
    return _PYCAW_IMPORT_ERROR


def list_output_devices():
    """[{"id", "name", "is_default"}] for every ACTIVE render (playback)
    endpoint. Disabled/unplugged devices are left out — nothing useful
    to switch to there."""
    if _PYCAW_IMPORT_ERROR is not None:
        return []
    try:
        comtypes.CoInitialize()
    except Exception:
        pass  # already initialized on this thread — fine
    try:
        default_id = None
        speakers = AudioUtilities.GetSpeakers()
        if speakers is not None:
            default_id = speakers.GetId()
    except Exception:
        default_id = None

    out = []
    try:
        for dev in AudioUtilities.GetAllDevices():
            if dev is None:
                continue
            try:
                if dev.state != AudioDeviceState.Active:
                    continue
                out.append({
                    "id": dev.id,
                    "name": _friendly_name(dev),
                    "is_default": dev.id == default_id,
                })
            except Exception:
                continue
    except Exception:
        return []
    return out


def set_default_output_device(device_id):
    """Switches the system default playback device (all three roles).
    Returns {"ok": bool, "error": str|None}."""
    if _PYCAW_IMPORT_ERROR is not None:
        return {"ok": False, "error": "Audio Output switching unavailable: " + _PYCAW_IMPORT_ERROR}
    try:
        comtypes.CoInitialize()
    except Exception:
        pass
    try:
        policy_config = comtypes.CoCreateInstance(
            CLSID_CPolicyConfigClient, IPolicyConfig, comtypes.CLSCTX_ALL
        )
        for role in (ERole.eConsole, ERole.eMultimedia, ERole.eCommunications):
            policy_config.SetDefaultEndpoint(device_id, role.value)
        return {"ok": True, "error": None}
    except Exception as e:
        return {"ok": False, "error": str(e)}
