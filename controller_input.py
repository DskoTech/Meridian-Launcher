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
X_HOLD_SECONDS = 2  # hold X this long on an open-programs bar item to close it
B_HOLD_SECONDS = 2  # hold B this long to jump straight to Settings > System

DEFAULT_CONTROLS = {
    "confirm": "A",
    "back": "B",
    "up": "DPAD_UP",
    "down": "DPAD_DOWN",
    "left": "DPAD_LEFT",
    "right": "DPAD_RIGHT",
    # L3+R3 used to instantly quit the app; removed per user request — a
    # controller-only user with no other way out of Meridian Launcher was
    # one accidental double-click of the sticks away from losing the app
    # with no confirmation. Empty means the combo is disabled outright,
    # not "use the old default" — see the .get() calls below, which no
    # longer supply that default either.
    "quit_combo": [],
    "foreground_combo": ["START", "BACK"],
    "deadzone": 0.25,
    "cooldown_ms": 200,
}


class ControllerListener:
    def __init__(self, controls, on_action, on_any, on_quit_combo, on_foreground_combo,
                 on_raw_button=None, on_y_hold_complete=None, foreground_trigger_getter=None,
                 cooldown_scale_getter=None,
                 prefer_xinput=False, input_backend=None):
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
        input_backend: "xinput" (default), "gameinput", "directinput",
            "sdl3", or "auto" (try all four, XInput first) — the
            persisted Settings > Controls choice. prefer_xinput is kept
            for backwards compatibility and just forces "xinput" if set,
            same as before this option existed.
        """
        if prefer_xinput:
            prefer = ("xinput",)
        elif input_backend and input_backend != "auto":
            prefer = (input_backend,)
        else:
            prefer = ("xinput", "gameinput", "directinput", "sdl3")
        self.gamepad = open_gamepad(prefer=prefer)
        self.input_backend = input_backend or "xinput"
        self.prefer_xinput = bool(prefer_xinput)
        self.controls = controls
        self.on_action = on_action
        self.on_any = on_any
        self.on_quit_combo = on_quit_combo
        self.on_foreground_combo = on_foreground_combo
        self.on_raw_button = on_raw_button
        self.on_y_hold_complete = on_y_hold_complete
        self._stop = threading.Event()
        self.last_connected = False  # did the most recent poll see a controller?
        self._last_fire = {}
        self._prev_buttons = 0
        self._combo_latch = {"quit": False, "foreground": False, "shoulders": False}
        self._y_hold_start = None
        self._y_fired = False
        self._x_hold_start = None
        self._x_fired = False
        self._b_hold_start = None
        self._b_fired = False
        # returns "start_select" | "xbox" | "off" — how to bring the app to
        # the foreground. Read fresh each poll so Settings changes apply live.
        self._fg_getter = foreground_trigger_getter
        # optional callable -> float; scales the directional cooldown live
        # (e.g. 0.77 to make a section's navigation ~1.3x faster).
        self._cooldown_scale_getter = cooldown_scale_getter

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
        if self._cooldown_scale_getter:
            try:
                scale = float(self._cooldown_scale_getter())
                if scale > 0:
                    cooldown *= scale
            except Exception:
                pass
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
                # Foreground trigger is a user setting: Start+Select
                # together, the Guide/Xbox button, or off. (BACK is the
                # physical "Select"/"View" button in XInput terms.)
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

                # Start, pressed alone (not part of the Start+Back
                # foreground combo): opens a context menu on the current
                # selection where one exists (currently just the Photos
                # section's Edit / Set as Background popup).
                if "START" in rising and "BACK" not in pressed:
                    self.on_action("menu_start")

                # confirm / back as direct button mappings, edge-triggered
                for action_name in ("confirm", "back"):
                    btn = self.controls.get(action_name)
                    if btn and btn in rising:
                        self.on_action(action_name)

                # B held for B_HOLD_SECONDS -> on top of the normal tap-
                # triggered "back" action above (which already ran on the
                # rising edge - not suppressed here), also fires
                # "back_hold_system": jump straight into Settings > System
                # instead of just landing on the Sections bar the plain
                # back action leaves you on.
                back_btn = self.controls.get("back")
                if back_btn and back_btn in pressed:
                    if self._b_hold_start is None:
                        self._b_hold_start = time.time()
                        self._b_fired = False
                    elif not self._b_fired and (time.time() - self._b_hold_start) >= B_HOLD_SECONDS:
                        self._b_fired = True
                        self.on_action("back_hold_system")
                else:
                    self._b_hold_start = None
                    self._b_fired = False

                # Y quick-press (distinct from the 45s hold above) -> jump to
                # the subfolder/filter panel, same idea as the \ key
                if "Y" in rising:
                    self.on_action("y_subfolder")

                # X: quick press (release before X_HOLD_SECONDS) -> jump
                # to / away from the open-programs bar; held for
                # X_HOLD_SECONDS while on a bar item -> close that task.
                # Same press-vs-hold split as the Y handling above.
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

                # R3 (right stick click): stop music. Edge-triggered same
                # as every other single-button action.
                if "RIGHT_THUMB" in rising:
                    self.on_action("stop_music")

                # Right stick left/right: rewind/fast-forward the current
                # track by 10s. Edge-triggered on crossing the deadzone
                # (not cooldown-repeated like navigation) so a single
                # flick means a single 10s seek - holding the stick over
                # doesn't rapid-fire more seeks, it has to return to
                # center and be pushed again.
                rx = self._deadzone(snap.rx)
                if rx < 0:
                    if not self._combo_latch.get("rstick_seek"):
                        self._combo_latch["rstick_seek"] = True
                        self.on_action("seek_back_10")
                elif rx > 0:
                    if not self._combo_latch.get("rstick_seek"):
                        self._combo_latch["rstick_seek"] = True
                        self.on_action("seek_fwd_10")
                else:
                    self._combo_latch["rstick_seek"] = False

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
