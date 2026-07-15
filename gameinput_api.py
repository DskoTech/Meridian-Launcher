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
    # Guide / Xbox button. Not reported by the public XInputGetState, only
    # by the undocumented XInputGetStateEx (ordinal 100). Whether it's
    # populated depends on which entry point the active backend calls; when
    # it isn't available this bit simply never sets, and the Start+Select
    # fallback covers that case.
    "GUIDE": 0x0400,
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
    # GameInputGamepadGuide -> our synthetic GUIDE bit. GameInput reports
    # the Guide/Xbox button natively (unlike the public XInput API), so the
    # "Xbox button to foreground" setting works on the GameInput path.
    (0x00004000, 0x0400),  # Guide           -> GUIDE
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


# IGameInputReading::GetGamepadState vtable slots to try, best first.
#
# The docs put GetGamepadState at slot 22 (0-2 IUnknown, 3 GetInputKind,
# 4 GetSequenceNumber, 5 GetTimestamp, 6 GetDevice, 7 GetRawReport, 8-13
# controller axis/button/switch, 14-15 keys, 16 mouse, 17-18 touch,
# 19 motion, 20 arcade stick, 21 flight stick, 22 gamepad).
#
# In the field, though, the in-box Windows 11 gameinput.dll ACCESS VIOLATES
# on slot 22 and answers correctly on 23 — its vtable carries an extra entry
# ahead of the state getters. So 23 is tried first: it's the layout that
# actually ships, and it means the crashing slot is never touched on the
# machines that matter. 22 stays as a fallback for DLLs that match the docs.
# ctypes surfaces an access violation as OSError, so a wrong guess is caught
# by the probe's try/except rather than taking the app down.
GAMEPAD_STATE_SLOTS = (23, 22, 24)


# Live diagnostics for the Settings > Controller debugger. Cheap counters
# updated on every poll so a user can see exactly where GameInput stops.
DIAG = {
    "polls": 0,          # poll() calls
    "readings": 0,       # GetCurrentReading gave us a reading
    "no_reading": 0,     # ...and how often it didn't
    "states": 0,         # GetGamepadState filled a plausible state
    "state_false": 0,    # ...and how often it returned False
    "last_hr": None,     # last GetCurrentReading HRESULT
    "slot": None,        # the vtable slot that won
    "slot_probe": {},    # {slot: what happened}
    "stage": "not started",
    "last_state": None,   # last raw state, for the live readout
    "buttons_seen": 0,    # OR of every button mask ever decoded
    "stick_moved": False, # any stick pushed past 0.3
    "trigger_moved": False,
    "nonzero_states": 0,  # states where any button was down
}


def reset_diag():
    DIAG.update({
        "polls": 0, "readings": 0, "no_reading": 0, "states": 0,
        "state_false": 0, "last_hr": None, "slot": None,
        "slot_probe": {}, "stage": "not started", "last_state": None,
        "buttons_seen": 0, "stick_moved": False, "trigger_moved": False,
        "nonzero_states": 0,
    })


def _record_state(state):
    DIAG["last_state"] = {
        "buttons": "0x%08X" % state.buttons,
        "lt": round(state.leftTrigger, 3), "rt": round(state.rightTrigger, 3),
        "lx": round(state.leftThumbstickX, 3), "ly": round(state.leftThumbstickY, 3),
        "rx": round(state.rightThumbstickX, 3), "ry": round(state.rightThumbstickY, 3),
    }
    # Accumulate every button bit and any stick/trigger movement ever seen.
    # This is the decisive test for "is this vtable slot actually reading the
    # pad?" — a wrong-but-plausible slot returns zeros forever, which looks
    # identical to an idle controller in a single sample. Press every button
    # and waggle the sticks: if these stay empty, the slot is wrong.
    DIAG["buttons_seen"] |= state.buttons
    if (abs(state.leftThumbstickX) > 0.3 or abs(state.leftThumbstickY) > 0.3 or
            abs(state.rightThumbstickX) > 0.3 or abs(state.rightThumbstickY) > 0.3):
        DIAG["stick_moved"] = True
    if state.leftTrigger > 0.2 or state.rightTrigger > 0.2:
        DIAG["trigger_moved"] = True
    if state.buttons:
        DIAG["nonzero_states"] += 1


def _why_implausible(state):
    for label, v in (("lx", state.leftThumbstickX), ("ly", state.leftThumbstickY),
                     ("rx", state.rightThumbstickX), ("ry", state.rightThumbstickY)):
        if v != v:
            return "%s is NaN" % label
        if not (-1.05 <= v <= 1.05):
            return "%s out of range (%.3g)" % (label, v)
    for label, v in (("lt", state.leftTrigger), ("rt", state.rightTrigger)):
        if v != v:
            return "%s is NaN" % label
        if not (-0.05 <= v <= 1.05):
            return "%s out of range (%.3g)" % (label, v)
    return "buttons=0x%08X" % state.buttons


def _plausible_gamepad_state(state):
    """Sanity-check a filled gamepad state, so calling the wrong vtable slot
    is detected instead of feeding garbage into the input system.

    Only the float ranges are checked. The button mask deliberately is NOT
    validated against a known-bit list: a controller reporting a bit we
    haven't mapped is perfectly legal, and rejecting the whole state for that
    would turn an unknown button into total input loss.
    """
    for v in (state.leftThumbstickX, state.leftThumbstickY,
              state.rightThumbstickX, state.rightThumbstickY):
        if v != v or not (-1.05 <= v <= 1.05):  # v != v catches NaN
            return False
    for v in (state.leftTrigger, state.rightTrigger):
        if v != v or not (-0.05 <= v <= 1.05):
            return False
    return True


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
        self._gi_version = None

        for iid_str, version in (
            (_IID_IGameInput_V1, "v1"),  # in-box Win11 + newer redists
            (_IID_IGameInput_V0, "v0"),  # older redist
        ):
            iid = _GUID.from_string(iid_str)
            out = ctypes.c_void_p()
            # COM: the interface pointer is the first (this) argument.
            if qi(raw, ctypes.byref(iid), ctypes.byref(out)) == 0 and out.value:
                self._gi = out
                self._gi_version = version
                break

        # Release the original pointer from GameInputCreate (QI added a ref).
        # COM methods take the interface pointer as their first (this) arg.
        _com_method(raw, 2, ctypes.c_ulong)(raw)

        if self._gi_version is None:
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
        # which GAMEPAD_STATE_SLOTS entry actually worked (set on first poll);
        # surfaced in the settings status line for diagnosis.
        self.gamepad_state_slot = None

    def poll(self):
        """Return a GamepadSnapshot, or None if no gamepad is connected."""
        DIAG["polls"] += 1
        reading = ctypes.c_void_p()
        # COM: self._gi is the (this) pointer for IGameInput methods.
        hr = self._get_current_reading(
            self._gi, _GAMEINPUT_KIND_GAMEPAD, None, ctypes.byref(reading)
        )
        DIAG["last_hr"] = hr
        if hr < 0 or not reading.value:
            DIAG["no_reading"] += 1
            DIAG["stage"] = "GetCurrentReading returned no reading (HRESULT=0x%08X)" % (hr & 0xFFFFFFFF)
            return None  # no gamepad reading available (disconnected)
        DIAG["readings"] += 1

        try:
            if self._reading_release is None:
                self._reading_release = _com_method(reading, 2, ctypes.c_ulong)

            state = self._read_gamepad_state(reading)
            if state is None:
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

    def _read_gamepad_state(self, reading):
        """Call IGameInputReading::GetGamepadState on the reading.

        The slot is 22 in the documented IGameInputReading vtable (slot 17 is
        GetTouchCount — calling that instead is why a "working" GameInput can
        report no input at all). Because vtable layouts aren't something we
        can verify at build time, the first successful slot is discovered
        empirically from GAMEPAD_STATE_SLOTS and then cached, so a layout
        difference degrades to "try the next candidate" rather than silently
        producing dead input.
        """
        if self._reading_get_state is not None:
            state = _GameInputGamepadState()
            if self._reading_get_state(reading, ctypes.byref(state)):
                DIAG["states"] += 1
                DIAG["stage"] = "ok"
                _record_state(state)
                return state
            DIAG["state_false"] += 1
            DIAG["stage"] = "GetGamepadState (slot %s) returned False" % self.gamepad_state_slot
            return None

        for slot in GAMEPAD_STATE_SLOTS:
            try:
                fn = _com_method(
                    reading, slot, ctypes.c_bool,
                    ctypes.POINTER(_GameInputGamepadState),
                )
                state = _GameInputGamepadState()
                ok = fn(reading, ctypes.byref(state))
                plausible = ok and _plausible_gamepad_state(state)
                DIAG["slot_probe"][str(slot)] = (
                    "accepted" if plausible else
                    ("returned False" if not ok else "implausible state (%s)" % _why_implausible(state))
                )
                if plausible:
                    self._reading_get_state = fn
                    self.gamepad_state_slot = slot
                    DIAG["slot"] = slot
                    DIAG["states"] += 1
                    DIAG["stage"] = "ok"
                    _record_state(state)
                    return state
            except Exception as e:
                DIAG["slot_probe"][str(slot)] = "raised %s: %s" % (type(e).__name__, e)
                continue
        DIAG["stage"] = "no vtable slot produced a plausible gamepad state"
        return None

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
        self._get_state = None
        for name in ("xinput1_4", "xinput1_3", "xinput9_1_0"):
            try:
                lib = getattr(ctypes.windll, name)
                # Ordinal 100 is XInputGetStateEx, which additionally reports
                # the Guide/Xbox button (bit 0x0400). It's undocumented but
                # present in xinput1_3/1_4; fall back to the public function
                # when it can't be resolved.
                try:
                    ex = lib[100]
                    ex.argtypes = [ctypes.c_uint, ctypes.POINTER(_XINPUT_STATE)]
                    ex.restype = ctypes.c_uint
                    self._get_state = ex
                except Exception:
                    lib.XInputGetState.argtypes = [
                        ctypes.c_uint, ctypes.POINTER(_XINPUT_STATE)
                    ]
                    lib.XInputGetState.restype = ctypes.c_uint
                    self._get_state = lib.XInputGetState
                break
            except (OSError, AttributeError):
                lib = None
        if lib is None or self._get_state is None:
            raise OSError("no XInput DLL available")
        self._lib = lib
        self._state = _XINPUT_STATE()

    def poll(self):
        if self._get_state(0, ctypes.byref(self._state)) != 0:
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

    # Record why each backend was rejected, so the settings screen can show
    # *why* GameInput fell back to XInput (e.g. missing DLL vs. create fail).
    global LAST_BACKEND_ERRORS
    LAST_BACKEND_ERRORS = {}

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
            LAST_BACKEND_ERRORS[name] = "%s: %s" % (type(e).__name__, e)
            if log:
                log("gamepad backend %s unavailable: %s" % (name, e))
    return None


# Populated by open_gamepad(): {backend_name: "why it failed"} for backends
# that were tried and rejected. Surfaced in the controller-status settings
# line so a GameInput->XInput fallback is diagnosable in the field.
LAST_BACKEND_ERRORS = {}


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
