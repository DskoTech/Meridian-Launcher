"""
CyberDeck Controller Thread

Runs gamepad polling in a separate thread.

Backend order:

1. Windows GameInput API (gameinput_api.py) — the input path used by
   Windows 11's Xbox full screen experience ("Xbox mode"). Polling this
   first fixes the fullscreen-experience no-controls problem, and it
   also enumerates DualShock/Switch pads natively.
2. pygame / SDL joystick — previous behavior, widest desktop
   compatibility for exotic controllers.
3. Legacy XInput (also via gameinput_api.py) — last-ditch fallback.

Provides:
- Analog stick movement
- D-pad events
- Controller buttons
- Shoulder buttons
- Triggers

Signal surface, ControllerState fields, and sign conventions
(SDL style: stick Y down = +1, triggers -1..1) are unchanged, so
UI code connects exactly as before.
"""


from PySide6.QtCore import (
    QThread,
    Signal
)

import time

from controller.state import ControllerState


try:

    from gameinput_api import open_gamepad, XI_BUTTONS

    GAMEINPUT_AVAILABLE = True

except ImportError:

    GAMEINPUT_AVAILABLE = False


try:

    import pygame

    GAMEPAD_AVAILABLE = True


except ImportError:

    GAMEPAD_AVAILABLE = False


# How often to re-scan for a controller when none is connected (seconds)
_RESCAN_INTERVAL = 2.0


class ControllerThread(QThread):


    #
    # Buttons
    #

    a_pressed = Signal()

    b_pressed = Signal()

    x_pressed = Signal()

    y_pressed = Signal()


    start_pressed = Signal()

    select_pressed = Signal()


    lb_pressed = Signal()

    rb_pressed = Signal()


    l3_pressed = Signal()

    r3_pressed = Signal()


    #
    # D-pad
    #

    dpad_up = Signal()

    dpad_down = Signal()

    dpad_left = Signal()

    dpad_right = Signal()


    #
    # Analog movement
    #

    left_stick = Signal(float, float)

    right_stick = Signal(float, float)


    #
    # Triggers
    #

    left_trigger = Signal(float)

    right_trigger = Signal(float)


    # Named button order shared by every backend; index matches the old
    # SDL/XInput button numbering the signals were written against.
    _BUTTON_NAMES = (
        "a",       # 0
        "b",       # 1
        "x",       # 2
        "y",       # 3
        "lb",      # 4
        "rb",      # 5
        "select",  # 6
        "start",   # 7
        "l3",      # 8
        "r3",      # 9
    )

    def __init__(self, parent=None):
        super().__init__(parent)
        self.running = True
        self.pad = None            # gameinput_api backend (GameInput/XInput)
        self.controller = None     # pygame joystick fallback
        self.last_buttons = {}
        self.current_buttons = {}
        self.state = ControllerState()
        self._button_signals = None  # built lazily (signals bind per instance)

    # ------------------------------------------------------------------ #
    # Backend discovery
    # ------------------------------------------------------------------ #

    def initialize_controller(self):
        # 1) GameInput (fixes Xbox fullscreen experience; covers most pads)
        if GAMEINPUT_AVAILABLE and self.pad is None:
            try:
                self.pad = open_gamepad(prefer=("gameinput",))
            except Exception:
                self.pad = None
        if self.pad is not None:
            return

        # 2) pygame / SDL joystick (previous behavior)
        if GAMEPAD_AVAILABLE and self.controller is None:
            try:
                pygame.init()
                pygame.joystick.init()
                if pygame.joystick.get_count() > 0:
                    self.controller = pygame.joystick.Joystick(0)
                    self.controller.init()
            except Exception:
                self.controller = None
        if self.controller is not None:
            return

        # 3) legacy XInput
        if GAMEINPUT_AVAILABLE:
            try:
                self.pad = open_gamepad(prefer=("xinput",))
            except Exception:
                self.pad = None

    # ------------------------------------------------------------------ #
    # Per-backend sampling -> one normalized dict
    # ------------------------------------------------------------------ #

    def _sample_gameinput(self):
        try:
            snap = self.pad.poll()
        except Exception:
            snap = None
        if snap is None:
            return None
        b = snap.buttons
        return {
            "a": bool(b & XI_BUTTONS["A"]),
            "b": bool(b & XI_BUTTONS["B"]),
            "x": bool(b & XI_BUTTONS["X"]),
            "y": bool(b & XI_BUTTONS["Y"]),
            "start": bool(b & XI_BUTTONS["START"]),
            "select": bool(b & XI_BUTTONS["BACK"]),
            "lb": bool(b & XI_BUTTONS["LEFT_SHOULDER"]),
            "rb": bool(b & XI_BUTTONS["RIGHT_SHOULDER"]),
            "l3": bool(b & XI_BUTTONS["LEFT_THUMB"]),
            "r3": bool(b & XI_BUTTONS["RIGHT_THUMB"]),
            "dpad_up": bool(b & XI_BUTTONS["DPAD_UP"]),
            "dpad_down": bool(b & XI_BUTTONS["DPAD_DOWN"]),
            "dpad_left": bool(b & XI_BUTTONS["DPAD_LEFT"]),
            "dpad_right": bool(b & XI_BUTTONS["DPAD_RIGHT"]),
            # SDL conventions preserved: Y down = +1, triggers -1..1
            "lx": snap.lx,
            "ly": -snap.ly,
            "rx": snap.rx,
            "ry": -snap.ry,
            "lt": snap.lt * 2.0 - 1.0,
            "rt": snap.rt * 2.0 - 1.0,
        }

    def _sample_pygame(self):
        try:
            pygame.event.pump()
            j = self.controller
            nb = j.get_numbuttons()

            def btn(i):
                return bool(j.get_button(i)) if i < nb else False

            hat = j.get_hat(0) if j.get_numhats() > 0 else (0, 0)
            na = j.get_numaxes()

            def axis(i):
                return j.get_axis(i) if i < na else 0.0

            return {
                "a": btn(0), "b": btn(1), "x": btn(2), "y": btn(3),
                "lb": btn(4), "rb": btn(5),
                "select": btn(6), "start": btn(7),
                "l3": btn(8), "r3": btn(9),
                "dpad_up": hat[1] == 1,
                "dpad_down": hat[1] == -1,
                "dpad_left": hat[0] == -1,
                "dpad_right": hat[0] == 1,
                # same axis indices the previous version used
                "lx": axis(0), "ly": axis(1),
                "rx": axis(2), "ry": axis(3),
                "lt": axis(4), "rt": axis(5),
            }
        except Exception:
            return None

    # ------------------------------------------------------------------ #
    # Main loop
    # ------------------------------------------------------------------ #

    def run(self):
        self.initialize_controller()
        last_rescan = time.time()

        while self.running:
            sample = None
            if self.pad is not None:
                sample = self._sample_gameinput()
            elif self.controller is not None:
                sample = self._sample_pygame()
                if sample is None:
                    # pygame joystick died (unplugged) — drop it so the
                    # rescan below can pick something back up
                    self.controller = None

            if sample is None:
                self.state.connected = False
                now = time.time()
                if now - last_rescan >= _RESCAN_INTERVAL:
                    last_rescan = now
                    self.initialize_controller()
                time.sleep(0.5 if (self.pad is None and self.controller is None) else 0.016)
                continue

            self.state.connected = True
            self._apply(sample)
            time.sleep(0.016)

    def _apply(self, s):
        if self._button_signals is None:
            self._button_signals = {
                "a": self.a_pressed,
                "b": self.b_pressed,
                "x": self.x_pressed,
                "y": self.y_pressed,
                "start": self.start_pressed,
                "select": self.select_pressed,
                "lb": self.lb_pressed,
                "rb": self.rb_pressed,
                "l3": self.l3_pressed,
                "r3": self.r3_pressed,
            }

        #
        # Buttons: state + edge-triggered signals
        #

        self.current_buttons = {i: s[name] for i, name in enumerate(self._BUTTON_NAMES)}

        self.state.a = s["a"]
        self.state.b = s["b"]
        self.state.x = s["x"]
        self.state.y = s["y"]
        self.state.start = s["start"]
        self.state.select = s["select"]
        self.state.left_shoulder = s["lb"]
        self.state.right_shoulder = s["rb"]
        self.state.l3 = s["l3"]
        self.state.r3 = s["r3"]

        for i, name in enumerate(self._BUTTON_NAMES):
            self.check_button(i, self._button_signals[name])

        #
        # Analog sticks (deadzone applied, SDL sign convention)
        #

        deadzone = .15
        lx = 0 if abs(s["lx"]) < deadzone else s["lx"]
        ly = 0 if abs(s["ly"]) < deadzone else s["ly"]
        rx = 0 if abs(s["rx"]) < deadzone else s["rx"]
        ry = 0 if abs(s["ry"]) < deadzone else s["ry"]

        self.state.left_x = lx
        self.state.left_y = ly
        self.state.right_x = rx
        self.state.right_y = ry

        self.left_stick.emit(lx, ly)
        self.right_stick.emit(rx, ry)

        #
        # Triggers (-1 rest .. +1 fully pressed, as before)
        #

        self.state.left_trigger = s["lt"]
        self.state.right_trigger = s["rt"]
        self.left_trigger.emit(s["lt"])
        self.right_trigger.emit(s["rt"])

        #
        # D-pad (level-triggered while held, matching previous behavior)
        #

        self.state.dpad_up = s["dpad_up"]
        self.state.dpad_down = s["dpad_down"]
        self.state.dpad_left = s["dpad_left"]
        self.state.dpad_right = s["dpad_right"]

        if s["dpad_up"]:
            self.dpad_up.emit()
        elif s["dpad_down"]:
            self.dpad_down.emit()
        if s["dpad_left"]:
            self.dpad_left.emit()
        elif s["dpad_right"]:
            self.dpad_right.emit()

        self.last_buttons = self.current_buttons.copy()

    def check_button(self, index, signal):
        if (
            self.current_buttons.get(index)
            and
            not self.last_buttons.get(index)
        ):
            signal.emit()

    def stop(self):
        self.running = False
        self.quit()
        self.wait()
