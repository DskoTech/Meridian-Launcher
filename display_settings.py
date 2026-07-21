"""display_settings.py — resolution/refresh rate/HDR control for the
"Display & Audio" plug-on (System section).

Resolution + refresh rate go through pywin32's win32api
(EnumDisplaySettings/ChangeDisplaySettings) - a proven, already-correctly-
marshaled wrapper around the Win32 calls, so no hand-rolled ctypes structs
are needed for those two.

HDR ("Advanced Color") has no pywin32 wrapper - the only way to read/set it
is the documented but fiddly DisplayConfig API (QueryDisplayConfig +
DisplayConfigGetDeviceInfo/SetDeviceInfo). The structs below are hand-
defined via ctypes for that reason. Every buffer QueryDisplayConfig writes
into is allocated deliberately larger than the struct sizes require (both
extra array elements and a padding field appended to
DISPLAYCONFIG_PATH_INFO itself), specifically so that if this hand-written
layout is even slightly off from the real one, the failure mode is
reading/writing the wrong slice of a small, over-sized buffer - never
writing past the end of it. Only the first active display path is used
(this launcher's target use case is one TV/monitor on a couch setup, not
a multi-monitor desktop). Every function returns a plain {"ok": ...} dict
and never raises into its caller.
"""

import sys

IS_WINDOWS = sys.platform == "win32"


def list_display_modes():
    return {"modes": [], "current": None, "error": "Windows only."}


def set_display_mode(width, height, refresh_rate):
    return {"ok": False, "error": "Windows only."}


def get_hdr_state():
    return {"ok": False, "supported": False, "enabled": False, "error": "Windows only."}


def set_hdr_state(enable):
    return {"ok": False, "error": "Windows only."}


if IS_WINDOWS:
    import ctypes
    from ctypes import wintypes

    import win32api
    import win32con

    user32 = ctypes.windll.user32

    DM_PELSWIDTH = 0x80000
    DM_PELSHEIGHT = 0x100000
    DM_DISPLAYFREQUENCY = 0x400000

    def list_display_modes():
        try:
            modes = {}
            i = 0
            while i < 500:  # sanity cap - some drivers report huge/duplicate lists
                try:
                    dm = win32api.EnumDisplaySettings(None, i)
                except Exception:
                    break
                if dm is None:
                    break
                key = (dm.PelsWidth, dm.PelsHeight)
                modes.setdefault(key, set()).add(dm.DisplayFrequency)
                i += 1
            current = win32api.EnumDisplaySettings(None, win32con.ENUM_CURRENT_SETTINGS)
            out = []
            for (w, h), freqs in sorted(modes.items(), key=lambda kv: kv[0][0] * kv[0][1], reverse=True):
                if w < 640 or h < 480:
                    continue  # not a realistic desktop resolution - skip clutter
                out.append({"width": w, "height": h, "refresh_rates": sorted(freqs)})
            return {
                "modes": out,
                "current": {"width": current.PelsWidth, "height": current.PelsHeight,
                            "refresh_rate": current.DisplayFrequency},
                "error": None,
            }
        except Exception as e:
            return {"modes": [], "current": None, "error": str(e)}

    def set_display_mode(width, height, refresh_rate):
        try:
            dm = win32api.EnumDisplaySettings(None, win32con.ENUM_CURRENT_SETTINGS)
            dm.PelsWidth = int(width)
            dm.PelsHeight = int(height)
            dm.DisplayFrequency = int(refresh_rate)
            dm.Fields = DM_PELSWIDTH | DM_PELSHEIGHT | DM_DISPLAYFREQUENCY
            result = win32api.ChangeDisplaySettings(dm, 0)
            return {"ok": result == 0, "error": None if result == 0 else f"ChangeDisplaySettings returned {result}"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    # ---------------- HDR / Advanced Color ----------------
    QDC_ONLY_ACTIVE_PATHS = 0x00000002
    _GET_ADVANCED_COLOR_INFO = 9
    _SET_ADVANCED_COLOR_STATE = 10

    class LUID(ctypes.Structure):
        _fields_ = [("LowPart", wintypes.DWORD), ("HighPart", wintypes.LONG)]

    class _PathSourceInfo(ctypes.Structure):
        _fields_ = [
            ("adapterId", LUID), ("id", wintypes.UINT),
            ("modeInfoIdx", wintypes.UINT), ("statusFlags", wintypes.UINT),
        ]

    class _PathTargetInfo(ctypes.Structure):
        _fields_ = [
            ("adapterId", LUID), ("id", wintypes.UINT), ("modeInfoIdx", wintypes.UINT),
            ("outputTechnology", wintypes.UINT), ("rotation", wintypes.UINT),
            ("scaling", wintypes.UINT), ("refreshRateNumerator", wintypes.UINT),
            ("refreshRateDenominator", wintypes.UINT), ("scanLineOrdering", wintypes.UINT),
            ("targetAvailable", wintypes.BOOL), ("statusFlags", wintypes.UINT),
        ]

    class _PathInfo(ctypes.Structure):
        # `_pad` is deliberately bigger than any plausible slack the real
        # struct's own alignment could need - see module docstring. Only
        # element [0]'s sourceInfo/targetInfo/flags are ever read, so the
        # padding only has to guarantee "big enough to never overflow",
        # not "exactly right" for elements beyond the first.
        _fields_ = [
            ("sourceInfo", _PathSourceInfo), ("targetInfo", _PathTargetInfo),
            ("flags", wintypes.UINT), ("_pad", ctypes.c_byte * 64),
        ]

    class _ModeInfoOpaque(ctypes.Structure):
        # Real DISPLAYCONFIG_MODE_INFO is commonly ~64 bytes; this is
        # never read, only used to size the required buffer generously.
        _fields_ = [("raw", ctypes.c_byte * 256)]

    class _DeviceInfoHeader(ctypes.Structure):
        _fields_ = [("type", wintypes.UINT), ("size", wintypes.UINT), ("adapterId", LUID), ("id", wintypes.UINT)]

    class _GetAdvancedColorInfo(ctypes.Structure):
        _fields_ = [
            ("header", _DeviceInfoHeader), ("value", wintypes.UINT),
            ("colorEncoding", wintypes.UINT), ("bitsPerColorChannel", wintypes.UINT),
        ]

    class _SetAdvancedColorState(ctypes.Structure):
        _fields_ = [("header", _DeviceInfoHeader), ("value", wintypes.UINT)]

    def _find_active_target():
        """(LUID, target_id) for the first active display path, or None."""
        num_paths = wintypes.UINT(0)
        num_modes = wintypes.UINT(0)
        if user32.GetDisplayConfigBufferSizes(QDC_ONLY_ACTIVE_PATHS, ctypes.byref(num_paths),
                                              ctypes.byref(num_modes)) != 0:
            return None
        # Over-allocate: +8 elements of slack in case a display change
        # races between the size query and the real query below.
        paths = (_PathInfo * (num_paths.value + 8))()
        modes = (_ModeInfoOpaque * (num_modes.value + 8))()
        np2 = wintypes.UINT(num_paths.value)
        nm2 = wintypes.UINT(num_modes.value)
        ret = user32.QueryDisplayConfig(QDC_ONLY_ACTIVE_PATHS, ctypes.byref(np2), paths,
                                        ctypes.byref(nm2), modes, None)
        if ret != 0 or np2.value == 0:
            return None
        target = paths[0].targetInfo
        if not target.targetAvailable:
            return None
        return (target.adapterId, target.id)

    def get_hdr_state():
        try:
            found = _find_active_target()
            if found is None:
                return {"ok": False, "supported": False, "enabled": False, "error": "No active display found."}
            adapter_id, target_id = found
            info = _GetAdvancedColorInfo()
            info.header.type = _GET_ADVANCED_COLOR_INFO
            info.header.size = ctypes.sizeof(info)
            info.header.adapterId = adapter_id
            info.header.id = target_id
            ret = user32.DisplayConfigGetDeviceInfo(ctypes.byref(info))
            if ret != 0:
                return {"ok": False, "supported": False, "enabled": False,
                        "error": f"Couldn't read HDR state (code {ret})."}
            return {"ok": True, "supported": bool(info.value & 0x1), "enabled": bool(info.value & 0x2), "error": None}
        except Exception as e:
            return {"ok": False, "supported": False, "enabled": False, "error": str(e)}

    def set_hdr_state(enable):
        try:
            found = _find_active_target()
            if found is None:
                return {"ok": False, "error": "No active display found."}
            adapter_id, target_id = found
            state = _SetAdvancedColorState()
            state.header.type = _SET_ADVANCED_COLOR_STATE
            state.header.size = ctypes.sizeof(state)
            state.header.adapterId = adapter_id
            state.header.id = target_id
            state.value = 1 if enable else 0
            ret = user32.DisplayConfigSetDeviceInfo(ctypes.byref(state))
            return {"ok": ret == 0, "error": None if ret == 0 else f"Couldn't set HDR state (code {ret})."}
        except Exception as e:
            return {"ok": False, "error": str(e)}
