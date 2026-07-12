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


# Buttons watched for the kiosk-mode secret unlock sequence — reported via
# on_raw_button regardless of how the user has confirm/back/etc. remapped,
# since the code is meant to work no matter what the active control scheme is.
RAW_CODE_BUTTONS = {"DPAD_UP", "DPAD_DOWN", "DPAD_LEFT", "DPAD_RIGHT", "A", "B"}

# How long Y must be held continuously to disable kiosk mode.
Y_HOLD_SECONDS = 45.0

DEFAULT_CONTROLS = {
    "confirm": "A",
    "back": "B",
    "up": "DPAD_UP",
    "down": "DPAD_DOWN",
    "left": "DPAD_LEFT",
    "right": "DPAD_RIGHT",
    "quit_combo": ["LEFT_THUMB", "RIGHT_THUMB"],
    "foreground_combo": ["START", "BACK"],
    "deadzone": 0.25,
    "cooldown_ms": 200,
}


class ControllerListener:
    def __init__(self, controls, on_action, on_any, on_quit_combo, on_foreground_combo,
                 on_raw_button=None, on_y_hold_complete=None):
        """
        controls: dict following DEFAULT_CONTROLS shape (from controller_controls.json)
        on_action(action_name): called for confirm/back/up/down/left/right
        on_any(): called on any button press or stick/dpad activation
        on_quit_combo(): called when the quit combo is held
        on_foreground_combo(): called when the foreground combo is held
        on_raw_button(name): called on the rising edge of any button in
            RAW_CODE_BUTTONS, regardless of the active control mapping —
            used for the kiosk-mode secret unlock sequence.
        on_y_hold_complete(): called once after Y has been held continuously
            for Y_HOLD_SECONDS — another kiosk-mode exit path.
        """
        self.gamepad = open_gamepad()
        self.controls = controls
        self.on_action = on_action
        self.on_any = on_any
        self.on_quit_combo = on_quit_combo
        self.on_foreground_combo = on_foreground_combo
        self.on_raw_button = on_raw_button
        self.on_y_hold_complete = on_y_hold_complete
        self._stop = threading.Event()
        self._last_fire = {}
        self._prev_buttons = 0
        self._combo_latch = {"quit": False, "foreground": False, "shoulders": False}
        self._y_hold_start = None
        self._y_fired = False

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
            if snap is not None:  # controller connected
                pressed = self._button_names(snap.buttons)
                rising = pressed - self._button_names(self._prev_buttons)

                # combos
                quit_combo = set(self.controls.get("quit_combo", ["LEFT_THUMB", "RIGHT_THUMB"]))
                fg_combo = set(self.controls.get("foreground_combo", ["START", "BACK"]))
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

                # raw button reporting for the kiosk-mode secret unlock code —
                # always fires on the actual physical button, unaffected by remapping
                if self.on_raw_button:
                    for name in rising:
                        if name in RAW_CODE_BUTTONS:
                            self.on_raw_button(name)

                # Y held continuously for Y_HOLD_SECONDS -> kiosk-mode exit path
                if "Y" in pressed:
                    if self._y_hold_start is None:
                        self._y_hold_start = time.time()
                        self._y_fired = False
                    elif not self._y_fired and (time.time() - self._y_hold_start) >= Y_HOLD_SECONDS:
                        self._y_fired = True
                        if self.on_y_hold_complete:
                            self.on_y_hold_complete()
                else:
                    self._y_hold_start = None
                    self._y_fired = False

                # confirm / back as direct button mappings, edge-triggered
                for action_name in ("confirm", "back"):
                    btn = self.controls.get(action_name)
                    if btn and btn in rising:
                        self.on_action(action_name)

                # Y quick-press (distinct from the 45s hold above) -> jump to
                # the subfolder/filter panel, same idea as the \ key
                if "Y" in rising:
                    self.on_action("y_subfolder")

                # shoulders: single press = prev/next track, both held at
                # once = random track (edge-triggered, same latch pattern
                # as the quit/foreground combos above)
                if "LEFT_SHOULDER" in pressed and "RIGHT_SHOULDER" in pressed:
                    if not self._combo_latch["shoulders"]:
                        self._combo_latch["shoulders"] = True
                        self.on_action("random_track")
                else:
                    self._combo_latch["shoulders"] = False
                    if "LEFT_SHOULDER" in rising:
                        self.on_action("prev_track")
                    if "RIGHT_SHOULDER" in rising:
                        self.on_action("next_track")

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
                self._y_hold_start = None
                self._y_fired = False
            time.sleep(0.016)  # ~60Hz poll
