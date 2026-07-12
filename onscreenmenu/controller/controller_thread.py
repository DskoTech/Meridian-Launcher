"""
onscreenmenu Controller Thread

Background gamepad poller that publishes a shared ControllerState
read by InputManager, ControllerCursor, and MainWindow's combo
watcher every UI tick.

Backend order (via gameinput_api.open_gamepad):

1. Windows GameInput API — the input path used by Windows 11's
   Xbox full screen experience ("Xbox mode"). Polling this first
   fixes the fullscreen-experience no-controls problem.
2. Legacy XInput — fallback so nothing changes on systems
   without GameInput.

State conventions (what the rest of onscreenmenu was written
against):

    sticks   : -1.0 .. 1.0, screen convention (down = +1), so
               ControllerCursor can add left_y straight to a
               screen coordinate
    triggers : 0.0 (released) .. 1.0 (fully pressed) — cursor's
               trigger_boost checks `> 0.5`
    buttons  : plain bools, level state; consumers do their own
               edge detection against `last`

Because polling happens here (not tied to window focus or Qt
events), Start+Select hibernate and L3+R3 quit keep working even
while onscreenmenu is an invisible background overlay.
"""


import time

from PySide6.QtCore import QThread

from controller.state import ControllerState

from gameinput_api import open_gamepad, XI_BUTTONS


# How often to re-scan for a controller when none is connected (seconds)
_RESCAN_INTERVAL = 2.0

# Poll rate while a controller is connected (~60 Hz)
_POLL_SLEEP = 0.016


class ControllerThread(QThread):


    def __init__(self, parent=None):

        super().__init__(parent)

        self.running = True

        self.pad = None

        self.state = ControllerState()


    #
    # ---- backend discovery ----
    #

    def _open_backend(self):

        try:

            # GameInput first, XInput fallback (see module docstring)
            self.pad = open_gamepad()

        except Exception:

            self.pad = None


    #
    # ---- main loop ----
    #

    def run(self):

        self._open_backend()

        last_rescan = time.time()

        while self.running:

            snap = None

            if self.pad is not None:

                try:

                    snap = self.pad.poll()

                except Exception:

                    snap = None

            if snap is None:

                #
                # No controller (or no driver at all). Blank the
                # state so stale button values can't re-trigger
                # combos, then rescan occasionally.
                #

                if self.state.connected:

                    self.state = ControllerState()

                self.state.connected = False

                now = time.time()

                if self.pad is None and now - last_rescan >= _RESCAN_INTERVAL:

                    last_rescan = now

                    self._open_backend()

                time.sleep(0.25 if self.pad is None else _POLL_SLEEP)

                continue

            self._apply(snap)

            time.sleep(_POLL_SLEEP)


    def _apply(self, snap):

        s = self.state

        b = snap.buttons

        s.connected = True

        #
        # Buttons
        #

        s.a = bool(b & XI_BUTTONS["A"])
        s.b = bool(b & XI_BUTTONS["B"])
        s.x = bool(b & XI_BUTTONS["X"])
        s.y = bool(b & XI_BUTTONS["Y"])

        s.start = bool(b & XI_BUTTONS["START"])
        s.select = bool(b & XI_BUTTONS["BACK"])

        s.left_shoulder = bool(b & XI_BUTTONS["LEFT_SHOULDER"])
        s.right_shoulder = bool(b & XI_BUTTONS["RIGHT_SHOULDER"])

        s.l3 = bool(b & XI_BUTTONS["LEFT_THUMB"])
        s.r3 = bool(b & XI_BUTTONS["RIGHT_THUMB"])

        #
        # D-pad
        #

        s.dpad_up = bool(b & XI_BUTTONS["DPAD_UP"])
        s.dpad_down = bool(b & XI_BUTTONS["DPAD_DOWN"])
        s.dpad_left = bool(b & XI_BUTTONS["DPAD_LEFT"])
        s.dpad_right = bool(b & XI_BUTTONS["DPAD_RIGHT"])

        #
        # Sticks — snapshot is XInput convention (up = +1);
        # flip Y to screen convention (down = +1) for the cursor.
        #

        s.left_x = snap.lx
        s.left_y = -snap.ly

        s.right_x = snap.rx
        s.right_y = -snap.ry

        #
        # Triggers — already 0..1 in the snapshot
        #

        s.left_trigger = snap.lt
        s.right_trigger = snap.rt


    def stop(self):

        self.running = False

        self.quit()

        self.wait()

        if self.pad is not None:

            try:

                self.pad.close()

            except Exception:

                pass

            self.pad = None
