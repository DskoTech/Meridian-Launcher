"""Game controller support via the Windows GameInput API, with XInput
fallback. Polls in a background thread so combos like Start+Back (bring to
foreground) work even when the app window isn't focused.

GameInput is Microsoft's modern replacement for XInput/DirectInput and is
the input path used by Windows 11's Xbox full screen experience ("Xbox
mode"). Polling it first fixes the fullscreen-experience no-controls
problem; on systems without GameInput we fall back to classic XInput, so
behavior everywhere else is unchanged. All backend details live in
gameinput_api.py — this module keeps the same ControllerListener interface
it always had.
"""

import threading
import time

from gameinput_api import XI_BUTTONS as BUTTONS, open_gamepad


DEFAULT_CONTROLS = {
    "confirm": "A",
    "back": "B",
    "up": "DPAD_UP",
    "down": "DPAD_DOWN",
    "left": "DPAD_LEFT",
    "right": "DPAD_RIGHT",
    # L3+R3 used to instantly quit the app; removed for consistency with
    # Meridian Launcher — a controller-only user with no other way out
    # was one accidental double-click of the sticks away from losing the
    # app with no confirmation. Empty means the combo is disabled
    # outright, not "use the old default" — see the .get() call below,
    # which no longer supplies that default either.
    "quit_combo": [],
    "foreground_combo": ["START", "BACK"],
    "deadzone": 0.25,
    "cooldown_ms": 200,
}


X_HOLD_SECONDS = 3  # hold X this long on an open-programs bar item to close it


class ControllerListener:
    def __init__(self, controls, on_action, on_any, on_quit_combo, on_foreground_combo,
                 foreground_trigger_getter=None,
                 prefer_xinput=False):
        """
        controls: dict following DEFAULT_CONTROLS shape (from controller_controls.json)
        on_action(action_name): called for confirm/back/up/down/left/right
        on_any(): called on any button press or stick/dpad activation
        on_quit_combo(): called when the quit combo is held
        on_foreground_combo(): called when the foreground combo is held
        """
        # prefer_xinput forces the XInput backend; otherwise GameInput is
        # tried first and falls back to XInput on its own.
        self.gamepad = open_gamepad(prefer=("xinput",) if prefer_xinput else None)
        self.prefer_xinput = bool(prefer_xinput)
        self.controls = controls
        self.on_action = on_action
        self.on_any = on_any
        self.on_quit_combo = on_quit_combo
        self.on_foreground_combo = on_foreground_combo
        self._stop = threading.Event()
        self.last_connected = False  # did the most recent poll see a controller?
        self._last_fire = {}
        self._prev_buttons = 0
        self._combo_latch = {"quit": False, "foreground": False}
        self._fg_getter = foreground_trigger_getter
        # X press/hold tracking for the open-programs bar: a quick tap jumps
        # to/from the bar, a 3s hold closes the highlighted task. These are
        # read every poll in _loop(), so they must exist from construction.
        self._x_hold_start = None
        self._x_fired = False

    def status(self):
        """Which input backend this listener is using and whether a
        controller is currently talking to it — for the settings screen's
        diagnostic line (e.g. to see whether GameInput is actually the
        active path in a fullscreen experience)."""
        return {
            "backend": getattr(self.gamepad, "backend", None) if self.gamepad else None,
            "connected": bool(self.gamepad) and self.last_connected,
        }

    def start(self):
        if self.gamepad is None:
            return  # no controller driver available; app still works with kb/mouse
        threading.Thread(target=self._loop, daemon=True).start()

    def stop(self):
        self._stop.set()

    def _deadzone(self, norm):
        # norm is already a float in -1.0 .. 1.0 (GamepadSnapshot convention)
        dz = self.controls.get("deadzone", 0.25)
        if abs(norm) < dz:
            return 0.0
        return norm

    def _can_fire(self, action):
        cooldown = self.controls.get("cooldown_ms", 200) / 1000.0
        now = time.time()
        last = self._last_fire.get(action, 0)
        if now - last >= cooldown:
            self._last_fire[action] = now
            return True
        return False

    def _button_names(self, mask):
        return {name for name, bit in BUTTONS.items() if mask & bit}

    def _loop(self):
        while not self._stop.is_set():
            snap = None
            try:
                snap = self.gamepad.poll()
            except Exception:
                snap = None
            self.last_connected = snap is not None
            if snap is not None:  # controller connected
                pressed = self._button_names(snap.buttons)
                rising = pressed - self._button_names(self._prev_buttons)

                # combos
                quit_combo = set(self.controls.get("quit_combo", []))
                fg_mode = self._fg_getter() if self._fg_getter else "start_select"
                if fg_mode == "xbox":
                    fg_combo = {"GUIDE"}
                elif fg_mode == "off":
                    fg_combo = set()
                else:
                    fg_combo = {"START", "BACK"}
                if quit_combo and quit_combo.issubset(pressed):
                    if not self._combo_latch["quit"]:
                        self._combo_latch["quit"] = True
                        self.on_quit_combo()
                else:
                    self._combo_latch["quit"] = False

                if fg_combo and fg_combo.issubset(pressed):
                    if not self._combo_latch["foreground"]:
                        self._combo_latch["foreground"] = True
                        self.on_foreground_combo()
                else:
                    self._combo_latch["foreground"] = False

                if rising:
                    self.on_any()

                # confirm / back as direct button mappings, edge-triggered
                for action_name in ("confirm", "back"):
                    btn = self.controls.get(action_name)
                    if btn and btn in rising:
                        self.on_action(action_name)

                # Y quick-press (distinct from any hold-based feature) ->
                # jump to the filter/subfolder panel, same idea as the \ key
                if "Y" in rising:
                    self.on_action("y_subfolder")

                # X: quick press -> toggle the open-programs bar; hold 3s on
                # a bar item -> close it (press/hold split like Y above).
                if "X" in pressed:
                    if self._x_hold_start is None:
                        self._x_hold_start = time.time()
                        self._x_fired = False
                    elif not self._x_fired and (time.time() - self._x_hold_start) >= X_HOLD_SECONDS:
                        self._x_fired = True
                        self.on_action("x_taskbar_hold")
                else:
                    if self._x_hold_start is not None and not self._x_fired:
                        self.on_action("x_taskbar")
                    self._x_hold_start = None
                    self._x_fired = False

                # Left Trigger: toggle the overlay. The triggers are the only
                # controller inputs the suite doesn't already use (every face
                # button, shoulder, stick-click, Start/Back and Guide are
                # spoken for), so LT is the free one. Edge-triggered via a
                # latch so holding it doesn't strobe the overlay.
                if snap.lt > 0.6:
                    if not self._combo_latch.get("lt_overlay"):
                        self._combo_latch["lt_overlay"] = True
                        self.on_action("toggle_overlay")
                else:
                    self._combo_latch["lt_overlay"] = False

                # Start quick-press -> in-app Start menu. Gated on BACK not
                # being held so it doesn't also fire while doing the
                # Start+Back bring-to-foreground combo.
                if "START" in rising and "BACK" not in pressed:
                    self.on_action("start_menu")

                # directional: dpad OR left stick, cooldown-repeated while held
                lx = self._deadzone(snap.lx)
                ly = self._deadzone(snap.ly)
                dirs_active = set()
                if "DPAD_UP" in pressed or ly > 0:
                    dirs_active.add("up")
                if "DPAD_DOWN" in pressed or ly < 0:
                    dirs_active.add("down")
                if "DPAD_LEFT" in pressed or lx < 0:
                    dirs_active.add("left")
                if "DPAD_RIGHT" in pressed or lx > 0:
                    dirs_active.add("right")

                if dirs_active:
                    self.on_any()
                for d in dirs_active:
                    if self._can_fire(d):
                        self.on_action(d)

                self._prev_buttons = snap.buttons
            else:
                # controller disconnected: clear edge/latch state so nothing
                # fires spuriously when it comes back
                self._prev_buttons = 0
                self._combo_latch = {k: False for k in self._combo_latch}
            time.sleep(0.016)  # ~60Hz poll
