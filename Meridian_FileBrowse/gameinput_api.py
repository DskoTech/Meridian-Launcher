"""Meridian suite gamepad backend: Windows GameInput API with XInput fallback.

Why this exists
---------------
Windows 11's Xbox full screen experience / "Xbox mode" (handhelds like the
ROG Xbox Ally, and any PC with FSE force-enabled) routes controller input
through the modern GameInput stack. Apps that only poll legacy XInput or
SDL/pygame joysticks can end up with no controller input at all in that
environment ("fullscreen experience no controls"). GameInput is Microsoft's
replacement API for XInput/DirectInput and is the supported input path
there, while still working fine on a normal Windows desktop (Windows 10
19H1+ via the GameInput redistributable, in-box on Windows 11).

This module binds gameinput.dll directly with ctypes (Nano-COM, no
dependencies) and exposes one tiny surface that every Meridian app uses:

    pad = open_gamepad()          # GameInput if available, else XInput
    snap = pad.poll()             # -> GamepadSnapshot or None
    snap.buttons                  # XInput-style wButtons bitmask
    snap.lx, snap.ly, ...         # normalized floats

The snapshot deliberately uses the *XInput* button bitmask and sign
conventions (stick Y: up = +1) so existing Meridian code keeps working
unchanged regardless of which backend supplied the data.

Version handling
----------------
GameInput has versioned COM interfaces with different vtable layouts:

  * v1+ (Windows 11 in-box gameinput.dll, and the Microsoft.GameInput
    redistributable v1/v2/v3 — newer DLLs answer QueryInterface for the
    v1 IIDs for backwards compatibility):
      IGameInput        IID 40FFB7E4-6150-407A-B439-132BADC08D2D
      IGameInputReading IID 86318E60-0B3C-40D6-BEFA-C62F2D952724
      IGameInputReading::GetGamepadState = vtable slot 17

  * v0 (original GDK-era redistributable that many games installed):
      IGameInput        IID 11BE2A7E-4254-445A-9C09-FFC40F006918
      IGameInputReading IID 2156947A-E1FA-4DE0-A30B-D812931DBD8D
      IGameInputReading::GetGamepadState = vtable slot 22

We call GameInputCreate() once, then QueryInterface for the v1 IGameInput;
if the installed DLL is too old for that we fall back to the v0 interface.
GetCurrentReading sits at the same slot (4) in both versions; only the
reading interface layout differs.

Backend override (debugging): set the environment variable
MERIDIAN_INPUT_BACKEND to "gameinput", "xinput", or "none".
"""

import ctypes
import os
import sys
import time

IS_WINDOWS = sys.platform == "win32"

# ---------------------------------------------------------------------------
# Common snapshot type (XInput conventions)
# ---------------------------------------------------------------------------

# XInput-style button bitmask (what all existing Meridian code expects)
XI_BUTTONS = {
    "DPAD_UP": 0x0001, "DPAD_DOWN": 0x0002, "DPAD_LEFT": 0x0004, "DPAD_RIGHT": 0x0008,
    "START": 0x0010, "BACK": 0x0020,
    "LEFT_THUMB": 0x0040, "RIGHT_THUMB": 0x0080,
    "LEFT_SHOULDER": 0x0100, "RIGHT_SHOULDER": 0x0200,
    "A": 0x1000, "B": 0x2000, "X": 0x4000, "Y": 0x8000,
}


class GamepadSnapshot:
    """One frame of gamepad state, normalized to XInput conventions.

    buttons : int   XInput wButtons bitmask (see XI_BUTTONS)
    lt, rt  : float triggers, 0.0 (released) .. 1.0 (fully pressed)
    lx, ly  : float left stick, -1.0 .. 1.0  (ly: up = +1, XInput convention)
    rx, ry  : float right stick, -1.0 .. 1.0 (ry: up = +1)
    """

    __slots__ = ("buttons", "lt", "rt", "lx", "ly", "rx", "ry")

    def __init__(self, buttons=0, lt=0.0, rt=0.0, lx=0.0, ly=0.0, rx=0.0, ry=0.0):
        self.buttons = buttons
        self.lt = lt
        self.rt = rt
        self.lx = lx
        self.ly = ly
        self.rx = rx
        self.ry = ry


# ---------------------------------------------------------------------------
# GameInput backend (Nano-COM via ctypes)
# ---------------------------------------------------------------------------

class _GUID(ctypes.Structure):
    _fields_ = [
        ("Data1", ctypes.c_uint32),
        ("Data2", ctypes.c_uint16),
        ("Data3", ctypes.c_uint16),
        ("Data4", ctypes.c_ubyte * 8),
    ]

    @classmethod
    def from_string(cls, s):
        # "40FFB7E4-6150-407A-B439-132BADC08D2D"
        parts = s.split("-")
        d4_hex = parts[3] + parts[4]
        d4 = (ctypes.c_ubyte * 8)(*[int(d4_hex[i:i + 2], 16) for i in range(0, 16, 2)])
        return cls(int(parts[0], 16), int(parts[1], 16), int(parts[2], 16), d4)


# IIDs (see module docstring for provenance)
_IID_IGameInput_V1 = "40FFB7E4-6150-407A-B439-132BADC08D2D"
_IID_IGameInput_V0 = "11BE2A7E-4254-445A-9C09-FFC40F006918"

# GameInput enums / flags (identical in v0 and v1 headers)
_GAMEINPUT_KIND_GAMEPAD = 0x00040000

# GameInputGamepadButtons -> XInput wButtons
_GI_TO_XI = (
    (0x00000001, 0x0010),  # Menu           -> START
    (0x00000002, 0x0020),  # View           -> BACK
    (0x00000004, 0x1000),  # A
    (0x00000008, 0x2000),  # B
    (0x00000010, 0x4000),  # X
    (0x00000020, 0x8000),  # Y
    (0x00000040, 0x0001),  # DPadUp
    (0x00000080, 0x0002),  # DPadDown
    (0x00000100, 0x0004),  # DPadLeft
    (0x00000200, 0x0008),  # DPadRight
    (0x00000400, 0x0100),  # LeftShoulder
    (0x00000800, 0x0200),  # RightShoulder
    (0x00001000, 0x0040),  # LeftThumbstick  -> LEFT_THUMB
    (0x00002000, 0x0080),  # RightThumbstick -> RIGHT_THUMB
)


class _GameInputGamepadState(ctypes.Structure):
    _fields_ = [
        ("buttons", ctypes.c_uint32),
        ("leftTrigger", ctypes.c_float),
        ("rightTrigger", ctypes.c_float),
        ("leftThumbstickX", ctypes.c_float),
        ("leftThumbstickY", ctypes.c_float),
        ("rightThumbstickX", ctypes.c_float),
        ("rightThumbstickY", ctypes.c_float),
    ]


def _com_method(obj_ptr, slot, restype, *argtypes):
    """Build a callable for vtable slot `slot` of the COM object at obj_ptr."""
    vtbl = ctypes.cast(
        obj_ptr, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))
    ).contents
    proto = ctypes.WINFUNCTYPE(restype, ctypes.c_void_p, *argtypes)
    return proto(vtbl[slot])


class GameInputGamepad:
    """Polls the first connected gamepad through gameinput.dll.

    Raises OSError / RuntimeError from __init__ if GameInput is unavailable
    (DLL missing, GameInput service disabled, or no supported interface).
    """

    backend = "GameInput"

    # HRESULT returned by GetCurrentReading when no matching reading exists
    _E_READING_NOT_FOUND = -2087976957  # 0x838A0003 as signed HRESULT
    _E_DEVICE_DISCONNECTED = -2087976959  # 0x838A0001

    def __init__(self):
        if not IS_WINDOWS:
            raise OSError("GameInput is Windows-only")

        # LOAD_LIBRARY_SEARCH_SYSTEM32-style safety: try the explicit
        # System32 path first, then the normal search order (covers the
        # redistributable on Windows 10).
        self._dll = None
        candidates = []
        windir = os.environ.get("SystemRoot") or os.environ.get("WINDIR")
        if windir:
            candidates.append(os.path.join(windir, "System32", "gameinput.dll"))
        candidates.append("gameinput.dll")
        last_err = None
        for cand in candidates:
            try:
                self._dll = ctypes.WinDLL(cand)
                break
            except OSError as e:
                last_err = e
        if self._dll is None:
            raise OSError("gameinput.dll not found: %s" % last_err)

        create = self._dll.GameInputCreate
        create.argtypes = [ctypes.POINTER(ctypes.c_void_p)]
        create.restype = ctypes.c_long

        raw = ctypes.c_void_p()
        hr = create(ctypes.byref(raw))
        if hr < 0 or not raw.value:
            raise RuntimeError("GameInputCreate failed: HRESULT=0x%08X" % (hr & 0xFFFFFFFF))

        # QueryInterface for a version whose vtable layout we know.
        # v1 first (in-box Win11 + all newer redists), then v0 (old redist).
        qi = _com_method(
            raw, 0, ctypes.c_long,
            ctypes.POINTER(_GUID), ctypes.POINTER(ctypes.c_void_p),
        )
        self._gi = ctypes.c_void_p()
        self._reading_gamepad_slot = None

        for iid_str, gamepad_slot in (
            (_IID_IGameInput_V1, 17),  # v1 IGameInputReading::GetGamepadState
            (_IID_IGameInput_V0, 22),  # v0 IGameInputReading::GetGamepadState
        ):
            iid = _GUID.from_string(iid_str)
            out = ctypes.c_void_p()
            if qi(ctypes.byref(iid), ctypes.byref(out)) == 0 and out.value:
                self._gi = out
                self._reading_gamepad_slot = gamepad_slot
                break

        # Release the original pointer from GameInputCreate (QI added a ref).
        _com_method(raw, 2, ctypes.c_ulong)()

        if self._reading_gamepad_slot is None:
            raise RuntimeError("gameinput.dll exposes no supported IGameInput version")

        # IGameInput::GetCurrentReading — slot 4 in both v0 and v1.
        self._get_current_reading = _com_method(
            self._gi, 4, ctypes.c_long,
            ctypes.c_uint32,                    # GameInputKind
            ctypes.c_void_p,                    # IGameInputDevice* (NULL = any)
            ctypes.POINTER(ctypes.c_void_p),    # IGameInputReading**
        )

        # NOTE: we deliberately do NOT call SetFocusPolicy. The PC default
        # delivers input regardless of window focus, which the Meridian
        # suite relies on (Start+Back bring-to-foreground combos, the
        # onscreenmenu overlay, kiosk-mode unlock codes).

        # Prototype cache for reading methods (built lazily per reading ptr
        # is wasteful; the vtable is shared, so cache after first reading).
        self._reading_get_state = None
        self._reading_release = None

    def poll(self):
        """Return a GamepadSnapshot, or None if no gamepad is connected."""
        reading = ctypes.c_void_p()
        hr = self._get_current_reading(
            _GAMEINPUT_KIND_GAMEPAD, None, ctypes.byref(reading)
        )
        if hr < 0 or not reading.value:
            return None  # no gamepad reading available (disconnected)

        try:
            if self._reading_get_state is None:
                self._reading_get_state = _com_method(
                    reading, self._reading_gamepad_slot, ctypes.c_bool,
                    ctypes.POINTER(_GameInputGamepadState),
                )
                self._reading_release = _com_method(reading, 2, ctypes.c_ulong)

            state = _GameInputGamepadState()
            ok = self._reading_get_state(reading, ctypes.byref(state))
            if not ok:
                return None

            mask = 0
            gi = state.buttons
            for gi_bit, xi_bit in _GI_TO_XI:
                if gi & gi_bit:
                    mask |= xi_bit

            return GamepadSnapshot(
                buttons=mask,
                lt=state.leftTrigger,
                rt=state.rightTrigger,
                lx=state.leftThumbstickX,
                ly=state.leftThumbstickY,
                rx=state.rightThumbstickX,
                ry=state.rightThumbstickY,
            )
        finally:
            # Every reading returned by GetCurrentReading holds a reference.
            self._reading_release(reading)

    def close(self):
        if getattr(self, "_gi", None) and self._gi.value:
            try:
                _com_method(self._gi, 2, ctypes.c_ulong)(self._gi)
            except Exception:
                pass
            self._gi = ctypes.c_void_p()


# ---------------------------------------------------------------------------
# XInput fallback backend
# ---------------------------------------------------------------------------

class _XINPUT_GAMEPAD(ctypes.Structure):
    _fields_ = [
        ("wButtons", ctypes.c_ushort),
        ("bLeftTrigger", ctypes.c_ubyte),
        ("bRightTrigger", ctypes.c_ubyte),
        ("sThumbLX", ctypes.c_short),
        ("sThumbLY", ctypes.c_short),
        ("sThumbRX", ctypes.c_short),
        ("sThumbRY", ctypes.c_short),
    ]


class _XINPUT_STATE(ctypes.Structure):
    _fields_ = [("dwPacketNumber", ctypes.c_ulong), ("Gamepad", _XINPUT_GAMEPAD)]


class XInputGamepad:
    """Legacy XInput poller (player 0). Fallback when GameInput is absent."""

    backend = "XInput"

    def __init__(self):
        if not IS_WINDOWS:
            raise OSError("XInput is Windows-only")
        lib = None
        for name in ("xinput1_4", "xinput1_3", "xinput9_1_0"):
            try:
                lib = getattr(ctypes.windll, name)
                lib.XInputGetState.argtypes = [
                    ctypes.c_uint, ctypes.POINTER(_XINPUT_STATE)
                ]
                lib.XInputGetState.restype = ctypes.c_uint
                break
            except (OSError, AttributeError):
                lib = None
        if lib is None:
            raise OSError("no XInput DLL available")
        self._lib = lib
        self._state = _XINPUT_STATE()

    def poll(self):
        if self._lib.XInputGetState(0, ctypes.byref(self._state)) != 0:
            return None  # ERROR_DEVICE_NOT_CONNECTED etc.
        pad = self._state.Gamepad
        return GamepadSnapshot(
            buttons=pad.wButtons,
            lt=pad.bLeftTrigger / 255.0,
            rt=pad.bRightTrigger / 255.0,
            lx=pad.sThumbLX / 32768.0,
            ly=pad.sThumbLY / 32768.0,
            rx=pad.sThumbRX / 32768.0,
            ry=pad.sThumbRY / 32768.0,
        )

    def close(self):
        pass


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def open_gamepad(prefer=None, log=None):
    """Return the best available gamepad backend, or None.

    prefer: optional iterable of backend names to try, in order.
            Defaults to ("gameinput", "xinput").
            The MERIDIAN_INPUT_BACKEND environment variable overrides this
            ("gameinput", "xinput", or "none").
    log:    optional callable(str) for a one-line startup notice.
    """
    if not IS_WINDOWS:
        return None

    env = os.environ.get("MERIDIAN_INPUT_BACKEND", "").strip().lower()
    if env == "none":
        return None
    if env in ("gameinput", "xinput"):
        prefer = (env,)
    elif prefer is None:
        prefer = ("gameinput", "xinput")

    for name in prefer:
        try:
            if name == "gameinput":
                pad = GameInputGamepad()
            elif name == "xinput":
                pad = XInputGamepad()
            else:
                continue
            if log:
                log("gamepad backend: %s" % pad.backend)
            return pad
        except Exception as e:
            if log:
                log("gamepad backend %s unavailable: %s" % (name, e))
    return None


# ---------------------------------------------------------------------------
# SDL/pygame-joystick-compatible shim (used by Meridian Explorer)
# ---------------------------------------------------------------------------

class SDLJoystickShim:
    """Wraps a backend from open_gamepad() in the pygame.joystick.Joystick
    read API, using the classic SDL XInput joystick layout that Meridian
    Explorer's handle_controller() was written against:

      buttons: 0 A, 1 B, 2 X, 3 Y, 4 LB, 5 RB, 6 Back/View, 7 Start/Menu,
               8 L3, 9 R3
      hat 0:   d-pad, (x, y) with up = +1
      axes:    0 LX, 1 LY (down = +1), 2 LT (-1..1),
               3 RX, 4 RY (down = +1), 5 RT (-1..1)
    """

    _BUTTON_BITS = (
        0x1000,  # 0 A
        0x2000,  # 1 B
        0x4000,  # 2 X
        0x8000,  # 3 Y
        0x0100,  # 4 LB
        0x0200,  # 5 RB
        0x0020,  # 6 Back
        0x0010,  # 7 Start
        0x0040,  # 8 L3
        0x0080,  # 9 R3
    )

    _POLL_INTERVAL = 0.008  # refresh at most ~125Hz; cached within a frame

    def __init__(self, pad):
        self._pad = pad
        self._snap = GamepadSnapshot()
        self._last_poll = 0.0

    # -- pygame.joystick.Joystick compatibility surface --

    def init(self):
        return self

    def get_name(self):
        return "Meridian %s Gamepad" % self._pad.backend

    def get_numbuttons(self):
        return len(self._BUTTON_BITS)

    def get_button(self, i):
        self._refresh()
        if 0 <= i < len(self._BUTTON_BITS):
            return 1 if self._snap.buttons & self._BUTTON_BITS[i] else 0
        return 0

    def get_numhats(self):
        return 1

    def get_hat(self, i):
        self._refresh()
        b = self._snap.buttons
        x = (1 if b & XI_BUTTONS["DPAD_RIGHT"] else 0) - (1 if b & XI_BUTTONS["DPAD_LEFT"] else 0)
        y = (1 if b & XI_BUTTONS["DPAD_UP"] else 0) - (1 if b & XI_BUTTONS["DPAD_DOWN"] else 0)
        return (x, y)

    def get_numaxes(self):
        return 6

    def get_axis(self, i):
        self._refresh()
        s = self._snap
        if i == 0:
            return s.lx
        if i == 1:
            return -s.ly           # SDL: down = +1
        if i == 2:
            return s.lt * 2.0 - 1.0  # SDL joystick trigger: -1 rest .. +1
        if i == 3:
            return s.rx
        if i == 4:
            return -s.ry
        if i == 5:
            return s.rt * 2.0 - 1.0
        return 0.0

    # -- internals --

    def _refresh(self):
        now = time.time()
        if now - self._last_poll < self._POLL_INTERVAL:
            return
        self._last_poll = now
        snap = None
        try:
            snap = self._pad.poll()
        except Exception:
            snap = None
        self._snap = snap if snap is not None else GamepadSnapshot()
