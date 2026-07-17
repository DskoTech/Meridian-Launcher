"""Meridian suite gamepad backend: XInput by default, with GameInput,
DirectInput, and SDL3 available as alternates.

Why this exists
---------------
Windows 11's Xbox full screen experience / "Xbox mode" (handhelds like the
ROG Xbox Ally, and any PC with FSE force-enabled) can route controller
input through the modern GameInput stack instead of legacy XInput, which
some apps otherwise miss entirely in that environment. GameInput was
explored here as a fix for that, but its vtable-slot-probing approach
(GameInputGamepadState isn't at a single documented, stable slot across
driver/DLL versions) turned out to only reliably decode BUTTONS in
practice — sticks and triggers never confirmed real movement across
multiple independent test reports, not just one machine. That's a real
bug in this probing approach, not a one-off local issue, so GameInput is
no longer the default.

XInput is the default backend now: it's the plain, stable, fully public
Win32 API (XInputGetState/XInputGetStateEx), unchanged in over a decade,
and correctly reports all buttons/triggers/sticks. DirectInput and SDL3
are available as alternates (a Settings > Controls option cycles through
them) for edge cases XInput doesn't cover (very old/exotic controllers
XInput doesn't recognize), and GameInput is still available too, for the
Xbox-FSE-only scenario it was originally added for.

    pad = open_gamepad()          # XInput by default, or whatever the
                                   # input_backend setting/env var picks
    snap = pad.poll()             # -> GamepadSnapshot or None
    snap.buttons                  # XInput-style wButtons bitmask
    snap.lx, snap.ly, ...         # normalized floats

The snapshot deliberately uses the *XInput* button bitmask and sign
conventions (stick Y: up = +1) so existing Meridian code keeps working
unchanged regardless of which backend supplied the data.

GameInput interface (confirmed, not guessed)
----------------------------------------------
GameInput has exactly one IGameInput/IGameInputReading interface pair in
the real Windows SDK header (10.0.26100.0) - confirmed against Odin's
vendor/windows/GameInput bindings, which are regenerated directly from
that header via a COM interface parser, not reverse-engineered from field
observation:

  IGameInput        IID 11BE2A7E-4254-445A-9C09-FFC40F006918
  IGameInputReading IID 2156947A-E1FA-4DE0-A30B-D812931DBD8D
  IGameInput::GetCurrentReading          = vtable slot 4
  IGameInputReading::GetGamepadState     = vtable slot 22

An earlier revision of this code also tried a second, different
IGameInput IID first (guessing GetGamepadState sat at slot 17 there),
based on field reports of gameinput.dll access-violating on slot 22.
That interface doesn't exist in the real header at all - QueryInterface
succeeding for a made-up IID anyway, then calling "slot 17" on it, was
actually calling GetTouchCount() (confirmed at slot 17 on the real
interface) and force-casting its result as a GamepadState. That explains
the exact symptom reported across multiple independent machines: buttons
"sort of" worked (adjacent/aliased memory), sticks/triggers never showed
real movement no matter how long you waited. Removed entirely now in
favor of the single, SDK-confirmed interface above.

Backend override (debugging): set the environment variable
MERIDIAN_INPUT_BACKEND to "xinput", "gameinput", "directinput", "sdl3", or
"none". The persisted Settings > Controls choice (store.py's
"input_backend") is used when the env var isn't set; see
controller_input.py for how that's threaded through.
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


# IGameInputReading::GetGamepadState vtable slot.
#
# REVERTED (for now): a prior revision of this file prioritized slot 22,
# based on documentation cross-checked against Odin's vendor/windows/
# GameInput bindings (regenerated from the real Windows SDK 10.0.26100.0
# GameInput.h header) - slot layout there is 0-2 IUnknown, 3
# GetInputKind, 4 GetSequenceNumber, 5 GetTimestamp, 6 GetDevice, 7
# GetRawReport, 8-13 controller axis/button/switch, 14-15 keys, 16 mouse,
# 17-18 touch, 19 motion, 20 arcade stick, 21 flight stick, 22 gamepad.
# That documentation is presumably still accurate for SOME machines, but
# prioritizing it correlated with MORE crashes being reported across
# other computers, not fewer - so until we have real crash-log data (see
# crash_logger.py, and gameinput_slot_diagnostic.py for the standalone
# per-slot tester) to actually explain that, this goes back to trying 23
# first, the configuration that was in use before that change. The list
# still radiates outward as a defensive scan; the probation mechanism
# below only ever locks a slot in once it's actually seen real stick/
# trigger movement (not just a plausible-looking static read), and any
# slot that raises an exception gets permanently blacklisted after the
# first try.
# ctypes surfaces an access violation as OSError, so a wrong guess is
# still caught by the probe's try/except rather than taking the app down.
GAMEPAD_STATE_SLOTS = (23, 22, 24, 21, 25)


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
        # REVERTED (for now): a prior revision of this file tried only the
        # single interface confirmed against Odin's vendor/windows/
        # GameInput bindings (IID 11BE2A7E..., "v0" below) - that's the
        # interface documented in the real Windows SDK 10.0.26100.0
        # header, but that change correlated with MORE crashes being
        # reported across other machines, not fewer. Until we have real
        # crash-log data (see crash_logger.py) to know why, this goes
        # back to trying v1 first, then v0 - the configuration that was
        # in use before that change.
        qi = _com_method(
            raw, 0, ctypes.c_long,
            ctypes.POINTER(_GUID), ctypes.POINTER(ctypes.c_void_p),
        )
        self._gi = ctypes.c_void_p()
        self._gi_version = None

        for iid_str, version in (
            (_IID_IGameInput_V1, "v1"),  # in-box Win11 + newer redists
            (_IID_IGameInput_V0, "v0"),  # older redist / confirmed-by-SDK-header interface
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

        # A slot can pass _plausible_gamepad_state() on the very first read
        # while still being the WRONG slot: an all-zero-but-in-range state
        # (buttons correct, stick/trigger floats never actually written by
        # that particular COM method - they just sit at ctypes' zero-init
        # default forever) looks identical to "idle controller" in a single
        # sample. So a slot isn't locked in permanently the instant it looks
        # plausible; it's kept on probation for _PROBATION_SECONDS, during
        # which every candidate slot is polled each round and the first one
        # to actually show stick or trigger movement wins outright. If
        # nothing shows movement before the deadline (button-only pad, or a
        # stick that genuinely never got touched during that window), the
        # first plausible candidate is locked in anyway so buttons keep
        # working rather than looping forever.
        self._PROBATION_SECONDS = 15.0
        self._probation_started = None
        self._probation_candidates = {}  # slot -> (fn, ever_moved: bool)
        self._probation_order = []       # slots in the order first seen plausible
        self._probation_blacklist = set()  # slots that raised - never retried

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
        can verify at build time, candidate slots are probed empirically
        from GAMEPAD_STATE_SLOTS; see the class docstring above __init__ for
        why a slot isn't locked in the instant it looks plausible (a slot
        whose analog fields are never actually written reads as a
        permanently-idle-but-in-range controller, which is indistinguishable
        from a real idle one in a single sample).
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

        now = time.time()
        if self._probation_started is None:
            self._probation_started = now

        best_state = None
        for slot in GAMEPAD_STATE_SLOTS:
            if slot in self._probation_blacklist:
                continue
            try:
                if slot in self._probation_candidates:
                    fn, _ = self._probation_candidates[slot]
                else:
                    fn = _com_method(
                        reading, slot, ctypes.c_bool,
                        ctypes.POINTER(_GameInputGamepadState),
                    )
                state = _GameInputGamepadState()
                ok = fn(reading, ctypes.byref(state))
                plausible = ok and _plausible_gamepad_state(state)
                DIAG["slot_probe"][str(slot)] = (
                    "accepted, probation" if plausible else
                    ("returned False" if not ok else "implausible state (%s)" % _why_implausible(state))
                )
                if not plausible:
                    continue

                if slot not in self._probation_candidates:
                    self._probation_candidates[slot] = (fn, False)
                    self._probation_order.append(slot)
                if best_state is None:
                    best_state = state  # first plausible candidate this round, for the caller

                moved = (abs(state.leftThumbstickX) > 0.3 or abs(state.leftThumbstickY) > 0.3 or
                         abs(state.rightThumbstickX) > 0.3 or abs(state.rightThumbstickY) > 0.3 or
                         state.leftTrigger > 0.2 or state.rightTrigger > 0.2)
                if moved:
                    self._probation_candidates[slot] = (fn, True)
                    DIAG["slot_probe"][str(slot)] = "accepted, confirmed by movement"
                    self._reading_get_state = fn
                    self.gamepad_state_slot = slot
                    DIAG["slot"] = slot
                    DIAG["states"] += 1
                    DIAG["stage"] = "ok (confirmed by real stick/trigger movement)"
                    _record_state(state)
                    return state
            except Exception as e:
                # Blacklisted permanently (not just "continue") - a slot that
                # access-violates must never be touched again, matching the
                # original safety guarantee (see GAMEPAD_STATE_SLOTS comment)
                # that a crashing slot is only ever tried once.
                self._probation_blacklist.add(slot)
                DIAG["slot_probe"][str(slot)] = "raised %s: %s (blacklisted)" % (type(e).__name__, e)
                continue

        # Nothing has shown real analog movement yet. Once the probation
        # window elapses, fall back to the first plausible candidate seen
        # (in GAMEPAD_STATE_SLOTS priority order) so buttons keep working
        # even on a controller whose sticks/triggers were never touched -
        # or one that genuinely has none.
        if self._probation_order and (now - self._probation_started) >= self._PROBATION_SECONDS:
            slot = self._probation_order[0]
            fn, _ = self._probation_candidates[slot]
            self._reading_get_state = fn
            self.gamepad_state_slot = slot
            DIAG["slot"] = slot
            DIAG["stage"] = "ok (probation timed out, no slot showed movement - locked to first plausible)"

        if best_state is not None:
            DIAG["states"] += 1
            _record_state(best_state)
            return best_state
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
    """Legacy XInput poller — polls ALL FOUR player slots (0-3) and merges
    them into one GamepadSnapshot, rather than only ever reading slot 0.
    XInput enumerates controllers into whichever of its 4 slots Windows
    assigns them, not necessarily slot 0 - with only one slot read, a
    second controller (or the first one, if Windows happened to assign it
    to slot 1/2/3) simply produced no input at all. Buttons are OR'd
    together; whichever stick/trigger has the largest magnitude across
    all connected pads wins for each axis - so either controller (or
    both, used loosely together) drives navigation."""

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
        self._states = [_XINPUT_STATE() for _ in range(4)]
        # Slots that returned ERROR_DEVICE_NOT_CONNECTED get re-checked
        # less often than connected ones (XInputGetState on an empty slot
        # is one of the slower calls in the API) - every 60th poll only,
        # so plugging a second controller in mid-session is still picked
        # up, just not at the cost of polling 3 empty slots every frame.
        self._slot_poll_count = 0
        self._known_connected = set()

    def poll(self):
        self._slot_poll_count += 1
        check_all = (self._slot_poll_count % 60) == 0
        best = None
        best_stick_mag = -1.0
        buttons = 0
        lt = rt = 0.0
        any_connected = False

        for slot in range(4):
            if slot not in self._known_connected and not check_all and slot != 0:
                continue
            state = self._states[slot]
            if self._get_state(slot, ctypes.byref(state)) != 0:
                self._known_connected.discard(slot)
                continue
            self._known_connected.add(slot)
            any_connected = True
            pad = state.Gamepad
            buttons |= pad.wButtons
            lt = max(lt, pad.bLeftTrigger / 255.0)
            rt = max(rt, pad.bRightTrigger / 255.0)
            lx, ly = pad.sThumbLX / 32768.0, pad.sThumbLY / 32768.0
            rx, ry = pad.sThumbRX / 32768.0, pad.sThumbRY / 32768.0
            mag = max(abs(lx), abs(ly), abs(rx), abs(ry))
            if best is None or mag > best_stick_mag:
                best_stick_mag = mag
                best = (lx, ly, rx, ry)

        if not any_connected:
            return None
        lx, ly, rx, ry = best or (0.0, 0.0, 0.0, 0.0)
        return GamepadSnapshot(
            buttons=buttons,
            lt=lt, rt=rt,
            lx=lx, ly=ly, rx=rx, ry=ry,
        )

    def close(self):
        pass


# ---------------------------------------------------------------------------
# DirectInput fallback backend
# ---------------------------------------------------------------------------
# Uses a CUSTOM data format rather than the classic c_dfDIJoystick2 - that
# symbol is a data table baked into the DirectX SDK's static dinput8.lib at
# link time, not something dinput8.dll exports at runtime, so it can't be
# pulled in with ctypes. DirectInput explicitly supports custom formats, so
# this defines a small one covering exactly what's needed: X/Y (left stick),
# Z/Rz (often the triggers on a combined axis, handled below), Rx/Ry (right
# stick on many drivers), one POV hat, and up to 16 buttons. The per-object
# GUIDs used (GUID_XAxis, GUID_Button, etc) are long-stable, documented in
# dinput.h since DirectX 5 and unchanged since.

class _DIOBJECTDATAFORMAT(ctypes.Structure):
    _fields_ = [
        ("pguid", ctypes.c_void_p),
        ("dwOfs", ctypes.c_ulong),
        ("dwType", ctypes.c_ulong),
        ("dwFlags", ctypes.c_ulong),
    ]


class _DIDATAFORMAT(ctypes.Structure):
    _fields_ = [
        ("dwSize", ctypes.c_ulong),
        ("dwObjSize", ctypes.c_ulong),
        ("dwFlags", ctypes.c_ulong),
        ("dwDataSize", ctypes.c_ulong),
        ("dwNumObjs", ctypes.c_ulong),
        ("rgodf", ctypes.POINTER(_DIOBJECTDATAFORMAT)),
    ]


class _DI_GUID(ctypes.Structure):
    _fields_ = [
        ("Data1", ctypes.c_ulong), ("Data2", ctypes.c_ushort), ("Data3", ctypes.c_ushort),
        ("Data4", ctypes.c_ubyte * 8),
    ]


def _guid(a, b, c, d):
    g = _DI_GUID(a, b, c, (ctypes.c_ubyte * 8)(*d))
    return g


# Standard DirectInput object-type GUIDs (dinput.h) - stable since DX5.
_DI_GUID_XAxis = _guid(0xA36D02E0, 0xC9F3, 0x11CF, (0xBF, 0xC7, 0x44, 0x45, 0x53, 0x54, 0x00, 0x00))
_DI_GUID_YAxis = _guid(0xA36D02E1, 0xC9F3, 0x11CF, (0xBF, 0xC7, 0x44, 0x45, 0x53, 0x54, 0x00, 0x00))
_DI_GUID_ZAxis = _guid(0xA36D02E2, 0xC9F3, 0x11CF, (0xBF, 0xC7, 0x44, 0x45, 0x53, 0x54, 0x00, 0x00))
_DI_GUID_RxAxis = _guid(0xA36D02F4, 0xC9F3, 0x11CF, (0xBF, 0xC7, 0x44, 0x45, 0x53, 0x54, 0x00, 0x00))
_DI_GUID_RyAxis = _guid(0xA36D02F5, 0xC9F3, 0x11CF, (0xBF, 0xC7, 0x44, 0x45, 0x53, 0x54, 0x00, 0x00))
_DI_GUID_RzAxis = _guid(0xA36D02E3, 0xC9F3, 0x11CF, (0xBF, 0xC7, 0x44, 0x45, 0x53, 0x54, 0x00, 0x00))
_DI_GUID_POV = _guid(0xA36D02C2, 0xC9F3, 0x11CF, (0xBF, 0xC7, 0x44, 0x45, 0x53, 0x54, 0x00, 0x00))
_DI_GUID_Button = _guid(0xA36D02F0, 0xC9F3, 0x11CF, (0xBF, 0xC7, 0x44, 0x45, 0x53, 0x54, 0x00, 0x00))

_DIIDFT_AXIS = 0x00000003
_DIIDFT_POV = 0x00000010
_DIIDFT_BUTTON = 0x0000000C
_DIDFT_ANYINSTANCE = 0x00FFFF00
_DIDOI_ASPECTPOSITION = 0x00000100

_NUM_DI_BUTTONS = 16


class _MeridianJoyState(ctypes.Structure):
    """Our own custom device-state struct, matching the field order/offsets
    used in _build_custom_format() below (X, Y, Z, Rx, Ry, Rz, one POV,
    then buttons)."""
    _fields_ = [
        ("lX", ctypes.c_long), ("lY", ctypes.c_long), ("lZ", ctypes.c_long),
        ("lRx", ctypes.c_long), ("lRy", ctypes.c_long), ("lRz", ctypes.c_long),
        ("dwPOV", ctypes.c_ulong),
        ("rgbButtons", ctypes.c_ubyte * _NUM_DI_BUTTONS),
    ]


def _build_custom_format():
    axis_flags = _DIDFT_ANYINSTANCE | _DIIDFT_AXIS
    fields = [
        (_DI_GUID_XAxis, 0), (_DI_GUID_YAxis, 4), (_DI_GUID_ZAxis, 8),
        (_DI_GUID_RxAxis, 12), (_DI_GUID_RyAxis, 16), (_DI_GUID_RzAxis, 20),
    ]
    objs = []
    guid_keepalive = []  # ctypes doesn't keep GUID structs alive via pguid alone
    for guid, ofs in fields:
        guid_keepalive.append(guid)
        objs.append(_DIOBJECTDATAFORMAT(ctypes.cast(ctypes.byref(guid), ctypes.c_void_p), ofs, axis_flags, 0))
    guid_keepalive.append(_DI_GUID_POV)
    objs.append(_DIOBJECTDATAFORMAT(ctypes.cast(ctypes.byref(_DI_GUID_POV), ctypes.c_void_p), 24, _DIDFT_ANYINSTANCE | _DIIDFT_POV, 0))
    for i in range(_NUM_DI_BUTTONS):
        guid_keepalive.append(_DI_GUID_Button)
        ofs = 28 + i
        objs.append(_DIOBJECTDATAFORMAT(ctypes.cast(ctypes.byref(_DI_GUID_Button), ctypes.c_void_p), ofs, _DIDFT_ANYINSTANCE | _DIIDFT_BUTTON, 0))
    arr = (_DIOBJECTDATAFORMAT * len(objs))(*objs)
    fmt = _DIDATAFORMAT(
        ctypes.sizeof(_DIDATAFORMAT), ctypes.sizeof(_DIOBJECTDATAFORMAT),
        0x00000001,  # DIDF_ABSAXIS
        ctypes.sizeof(_MeridianJoyState), len(objs), ctypes.cast(arr, ctypes.POINTER(_DIOBJECTDATAFORMAT)),
    )
    return fmt, arr, guid_keepalive  # caller must keep arr/guid_keepalive alive


class DirectInputGamepad:
    """Polls the first enumerated joystick/gamepad through dinput8.dll,
    using a custom (not the classic c_dfDIJoystick2) data format - see the
    section comment above for why. Raises OSError/RuntimeError from
    __init__ if DirectInput or a device isn't available."""

    backend = "DirectInput"

    IID_IDirectInput8W = _guid(0xBF798031, 0x483A, 0x4DA2, (0xAA, 0x99, 0x5D, 0x64, 0xED, 0x36, 0x97, 0x00))

    def __init__(self):
        if not IS_WINDOWS:
            raise OSError("DirectInput is Windows-only")
        try:
            dinput8 = ctypes.windll.dinput8
        except OSError as e:
            raise OSError("dinput8.dll not available: %s" % e)

        DirectInput8Create = dinput8.DirectInput8Create
        DirectInput8Create.argtypes = [
            ctypes.c_void_p, ctypes.c_ulong, ctypes.POINTER(_DI_GUID),
            ctypes.POINTER(ctypes.c_void_p), ctypes.c_void_p,
        ]
        DirectInput8Create.restype = ctypes.c_long

        hinst = ctypes.windll.kernel32.GetModuleHandleW(None)
        di_ptr = ctypes.c_void_p()
        hr = DirectInput8Create(hinst, 0x0800, ctypes.byref(self.IID_IDirectInput8W),
                                 ctypes.byref(di_ptr), None)
        if hr != 0 or not di_ptr:
            raise OSError("DirectInput8Create failed (hr=0x%08X)" % (hr & 0xFFFFFFFF))
        self._di = di_ptr

        # EnumDevices (slot 4): find the first attached joystick/gamepad.
        found = {"guid": None}
        DIENUM_CALLBACK = ctypes.WINFUNCTYPE(ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p)

        def _enum_cb(lpddi, pvRef):
            # DIDEVICEINSTANCEW: dwSize, GUID guidInstance, GUID guidProduct, ...
            guid_bytes = ctypes.string_at(lpddi + 4, ctypes.sizeof(_DI_GUID))
            found["guid"] = guid_bytes
            return 0  # DIENUM_STOP

        enum_devices = _com_method(self._di, 4, ctypes.c_long,
                                    ctypes.c_ulong, DIENUM_CALLBACK, ctypes.c_void_p, ctypes.c_ulong)
        cb = DIENUM_CALLBACK(_enum_cb)
        DI8DEVCLASS_GAMECTRL = 4
        DIEDFL_ATTACHEDONLY = 0x00000001
        enum_devices(self._di, DI8DEVCLASS_GAMECTRL, cb, None, DIEDFL_ATTACHEDONLY)
        if found["guid"] is None:
            self.close()
            raise OSError("no DirectInput game controller found")

        device_guid = _DI_GUID.from_buffer_copy(found["guid"])

        create_device = _com_method(self._di, 3, ctypes.c_long,
                                     ctypes.POINTER(_DI_GUID), ctypes.POINTER(ctypes.c_void_p), ctypes.c_void_p)
        dev_ptr = ctypes.c_void_p()
        hr = create_device(self._di, ctypes.byref(device_guid), ctypes.byref(dev_ptr), None)
        if hr != 0 or not dev_ptr:
            self.close()
            raise OSError("CreateDevice failed (hr=0x%08X)" % (hr & 0xFFFFFFFF))
        self._dev = dev_ptr

        self._fmt, self._fmt_objs, self._fmt_guids = _build_custom_format()
        set_data_format = _com_method(self._dev, 11, ctypes.c_long, ctypes.POINTER(_DIDATAFORMAT))
        hr = set_data_format(self._dev, ctypes.byref(self._fmt))
        if hr != 0:
            self.close()
            raise OSError("SetDataFormat failed (hr=0x%08X)" % (hr & 0xFFFFFFFF))

        acquire = _com_method(self._dev, 7, ctypes.c_long)
        acquire(self._dev)  # best-effort; GetDeviceState re-acquires on DIERR_INPUTLOST below

        self._get_state = _com_method(self._dev, 9, ctypes.c_long, ctypes.c_ulong, ctypes.c_void_p)
        self._acquire = acquire
        self._state = _MeridianJoyState()

    def poll(self):
        DIERR_INPUTLOST = -2147024882 & 0xFFFFFFFF  # 0x8007001E as signed
        DIERR_NOTACQUIRED = -2147417850 & 0xFFFFFFFF  # 0x8007001C as signed
        hr = self._get_state(self._dev, ctypes.sizeof(self._state), ctypes.byref(self._state))
        hru = hr & 0xFFFFFFFF
        if hru in (DIERR_INPUTLOST, DIERR_NOTACQUIRED):
            self._acquire(self._dev)
            hr = self._get_state(self._dev, ctypes.sizeof(self._state), ctypes.byref(self._state))
        if hr != 0:
            return None
        s = self._state
        # POV: 0..35900 (0.01 degree units) or 0xFFFFFFFF when centered.
        dpad_up = dpad_down = dpad_left = dpad_right = False
        if s.dwPOV != 0xFFFFFFFF:
            deg = s.dwPOV / 100.0
            if 315 <= deg or deg < 45:
                dpad_up = True
            if 45 <= deg < 135:
                dpad_right = True
            if 135 <= deg < 225:
                dpad_down = True
            if 225 <= deg < 315:
                dpad_left = True
        buttons = 0
        # First 10 buttons follow the common SDL/XInput-ish DirectInput
        # ordering many pads use: A,B,X,Y,LB,RB,Back,Start,L3,R3. This
        # varies more by controller than XInput does - a genuinely
        # non-standard pad may need its mapping adjusted here.
        bit_for_index = (
            XI_BUTTONS["A"], XI_BUTTONS["B"], XI_BUTTONS["X"], XI_BUTTONS["Y"],
            XI_BUTTONS["LEFT_SHOULDER"], XI_BUTTONS["RIGHT_SHOULDER"],
            XI_BUTTONS["BACK"], XI_BUTTONS["START"],
            XI_BUTTONS["LEFT_THUMB"], XI_BUTTONS["RIGHT_THUMB"],
        )
        for i, bit in enumerate(bit_for_index):
            if s.rgbButtons[i] & 0x80:
                buttons |= bit
        if dpad_up:
            buttons |= XI_BUTTONS["DPAD_UP"]
        if dpad_down:
            buttons |= XI_BUTTONS["DPAD_DOWN"]
        if dpad_left:
            buttons |= XI_BUTTONS["DPAD_LEFT"]
        if dpad_right:
            buttons |= XI_BUTTONS["DPAD_RIGHT"]

        def norm(v):
            return max(-1.0, min(1.0, v / 32767.0))

        # Most DirectInput pads report the two analog triggers combined on
        # the Z axis (full-negative..full-positive) rather than as two
        # independent axes the way XInput does - split it into two 0..1
        # trigger values as a reasonable default.
        z = norm(s.lZ - 32767)
        lt = max(0.0, -z)
        rt = max(0.0, z)
        return GamepadSnapshot(
            buttons=buttons,
            lt=lt, rt=rt,
            lx=norm(s.lX - 32767), ly=-norm(s.lY - 32767),
            rx=norm(s.lRx - 32767), ry=-norm(s.lRy - 32767),
        )

    def close(self):
        try:
            if getattr(self, "_dev", None):
                release = _com_method(self._dev, 2, ctypes.c_long)
                release(self._dev)
        except Exception:
            pass
        try:
            if getattr(self, "_di", None):
                release = _com_method(self._di, 2, ctypes.c_long)
                release(self._di)
        except Exception:
            pass


# ---------------------------------------------------------------------------
# SDL3 backend (optional - requires SDL3.dll on PATH or next to the exe)
# ---------------------------------------------------------------------------

class SDL3Gamepad:
    """Polls the first connected gamepad through SDL3's flat C gamepad API
    (SDL_OpenGamepad/SDL_GetGamepadAxis/SDL_GetGamepadButton) - a plain,
    stable exported-function ABI, not COM, so this is a much smaller
    binding than the GameInput/DirectInput backends above. Needs SDL3.dll
    present (bundled next to the exe, or already on PATH) - raises
    OSError/RuntimeError if it can't be loaded or no gamepad is found."""

    backend = "SDL3"

    SDL_INIT_GAMEPAD = 0x00002000
    _AXES = ("LEFTX", "LEFTY", "RIGHTX", "RIGHTY", "LEFT_TRIGGER", "RIGHT_TRIGGER")
    _BUTTONS = (
        ("SOUTH", "A"), ("EAST", "B"), ("WEST", "X"), ("NORTH", "Y"),
        ("BACK", "BACK"), ("START", "START"),
        ("LEFT_STICK", "LEFT_THUMB"), ("RIGHT_STICK", "RIGHT_THUMB"),
        ("LEFT_SHOULDER", "LEFT_SHOULDER"), ("RIGHT_SHOULDER", "RIGHT_SHOULDER"),
        ("DPAD_UP", "DPAD_UP"), ("DPAD_DOWN", "DPAD_DOWN"),
        ("DPAD_LEFT", "DPAD_LEFT"), ("DPAD_RIGHT", "DPAD_RIGHT"),
    )

    def __init__(self):
        if not IS_WINDOWS:
            raise OSError("this SDL3 binding only targets Windows")
        try:
            self._sdl = ctypes.CDLL("SDL3.dll")
        except OSError as e:
            raise OSError("SDL3.dll not found (place it next to the exe or on PATH): %s" % e)

        self._sdl.SDL_Init.argtypes = [ctypes.c_uint32]
        self._sdl.SDL_Init.restype = ctypes.c_bool
        if not self._sdl.SDL_Init(self.SDL_INIT_GAMEPAD):
            raise OSError("SDL_Init(SDL_INIT_GAMEPAD) failed")

        self._sdl.SDL_GetGamepads.argtypes = [ctypes.POINTER(ctypes.c_int)]
        self._sdl.SDL_GetGamepads.restype = ctypes.POINTER(ctypes.c_uint32)
        self._sdl.SDL_OpenGamepad.argtypes = [ctypes.c_uint32]
        self._sdl.SDL_OpenGamepad.restype = ctypes.c_void_p
        self._sdl.SDL_GetGamepadAxis.argtypes = [ctypes.c_void_p, ctypes.c_int]
        self._sdl.SDL_GetGamepadAxis.restype = ctypes.c_int16
        self._sdl.SDL_GetGamepadButton.argtypes = [ctypes.c_void_p, ctypes.c_int]
        self._sdl.SDL_GetGamepadButton.restype = ctypes.c_bool

        count = ctypes.c_int(0)
        ids = self._sdl.SDL_GetGamepads(ctypes.byref(count))
        if not ids or count.value <= 0:
            raise OSError("no SDL3 gamepad found")
        # Open EVERY connected gamepad, not just the first - a second
        # controller plugged in was previously never read at all.
        self._handles = []
        for i in range(count.value):
            h = self._sdl.SDL_OpenGamepad(ids[i])
            if h:
                self._handles.append(h)
        if not self._handles:
            raise OSError("SDL_OpenGamepad failed for every detected gamepad")
        self._handle = self._handles[0]  # kept for any legacy reference

        # SDL3's SDL_GamepadAxis/SDL_GamepadButton enums are stable public
        # ABI (0-based, in this fixed order) - named here rather than
        # imported since this is a minimal ctypes binding, not the full
        # SDL3 Python package.
        axis_names = ("LEFTX", "LEFTY", "RIGHTX", "RIGHTY", "LEFT_TRIGGER", "RIGHT_TRIGGER")
        self._axis_enum = {name: i + 1 for i, name in enumerate(axis_names)}  # SDL_GAMEPAD_AXIS_INVALID = -1, ...LEFTX = 0? see note below
        # Per SDL3's SDL_gamepad.h: SDL_GAMEPAD_AXIS_INVALID = -1,
        # LEFTX = 0, LEFTY = 1, RIGHTX = 2, RIGHTY = 3,
        # LEFT_TRIGGER = 4, RIGHT_TRIGGER = 5.
        self._axis_enum = {"LEFTX": 0, "LEFTY": 1, "RIGHTX": 2, "RIGHTY": 3,
                            "LEFT_TRIGGER": 4, "RIGHT_TRIGGER": 5}
        # Per SDL3's SDL_gamepad.h: SOUTH=0, EAST=1, WEST=2, NORTH=3,
        # BACK=4, GUIDE=5, START=6, LEFT_STICK=7, RIGHT_STICK=8,
        # LEFT_SHOULDER=9, RIGHT_SHOULDER=10, DPAD_UP=11, DPAD_DOWN=12,
        # DPAD_LEFT=13, DPAD_RIGHT=14.
        self._button_enum = {
            "SOUTH": 0, "EAST": 1, "WEST": 2, "NORTH": 3, "BACK": 4, "START": 6,
            "LEFT_STICK": 7, "RIGHT_STICK": 8, "LEFT_SHOULDER": 9, "RIGHT_SHOULDER": 10,
            "DPAD_UP": 11, "DPAD_DOWN": 12, "DPAD_LEFT": 13, "DPAD_RIGHT": 14,
        }

    def poll(self):
        if not self._handles:
            return None

        def axis(handle, name):
            return self._sdl.SDL_GetGamepadAxis(handle, self._axis_enum[name]) / 32767.0

        buttons = 0
        lt = rt = 0.0
        best = None
        best_mag = -1.0

        for handle in self._handles:
            for sdl_name, xi_name in self._BUTTONS:
                idx = self._button_enum.get(sdl_name)
                if idx is not None and self._sdl.SDL_GetGamepadButton(handle, idx):
                    buttons |= XI_BUTTONS[xi_name]
            lt = max(lt, max(0.0, axis(handle, "LEFT_TRIGGER")))
            rt = max(rt, max(0.0, axis(handle, "RIGHT_TRIGGER")))
            lx, ly = axis(handle, "LEFTX"), -axis(handle, "LEFTY")
            rx, ry = axis(handle, "RIGHTX"), -axis(handle, "RIGHTY")
            mag = max(abs(lx), abs(ly), abs(rx), abs(ry))
            if best is None or mag > best_mag:
                best_mag = mag
                best = (lx, ly, rx, ry)

        lx, ly, rx, ry = best or (0.0, 0.0, 0.0, 0.0)
        return GamepadSnapshot(
            buttons=buttons,
            lt=lt, rt=rt,
            lx=lx, ly=ly, rx=rx, ry=ry,
        )

    def close(self):
        try:
            self._sdl.SDL_CloseGamepad.argtypes = [ctypes.c_void_p]
            for handle in getattr(self, "_handles", []):
                self._sdl.SDL_CloseGamepad(handle)
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def open_gamepad(prefer=None, log=None):
    """Return the best available gamepad backend, or None.

    prefer: optional iterable of backend names to try, in order.
            Defaults to ("xinput", "gameinput", "directinput", "sdl3") -
            XInput first, since it's the plain stable public API and
            correctly reports every button/trigger/stick; the others are
            alternates for edge cases XInput doesn't cover.
            The MERIDIAN_INPUT_BACKEND environment variable overrides this
            ("xinput", "gameinput", "directinput", "sdl3", or "none").
    log:    optional callable(str) for a one-line startup notice.
    """
    if not IS_WINDOWS:
        return None

    env = os.environ.get("MERIDIAN_INPUT_BACKEND", "").strip().lower()
    if env == "none":
        return None
    if env in ("xinput", "gameinput", "directinput", "sdl3"):
        prefer = (env,)
    elif prefer is None:
        prefer = ("xinput", "gameinput", "directinput", "sdl3")

    # Record why each backend was rejected, so the settings screen can show
    # *why* the preferred backend fell back to the next one (e.g. missing
    # DLL vs. create fail vs. no device found).
    global LAST_BACKEND_ERRORS
    LAST_BACKEND_ERRORS = {}

    for name in prefer:
        try:
            if name == "xinput":
                pad = XInputGamepad()
            elif name == "gameinput":
                pad = GameInputGamepad()
            elif name == "directinput":
                pad = DirectInputGamepad()
            elif name == "sdl3":
                pad = SDL3Gamepad()
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
