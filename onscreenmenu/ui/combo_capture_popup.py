"""
onscreenmenu Combo Capture Popup

Shown during "Add Key Combo": counts down from 15 seconds while
the person holds down the keys for their combo, showing whichever
keys are currently held down in real time, then calls back with
whatever combo was captured.

This captures keys through Qt's normal keyPressEvent/
keyReleaseEvent on this popup itself (via an explicit keyboard
grab), NOT through a global OS-level keyboard hook. The global
hook approach (the `keyboard` package's hook()/add_hotkey()) turned
out to be unreliable for actually capturing presses depending on
the process's privilege level - this widget-focused approach only
needs normal Qt input delivery, which works regardless of whether
onscreenmenu is running elevated.

The saved combo is still played back later with `keyboard.send()`
(features/keycombo_manager.py) - that part is unaffected, since
sending synthetic input is a different, generally reliable
operation from hooking/capturing it.
"""

import math
import time

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel
)

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QKeySequence


DEFAULT_TIMEOUT = 15.0

TICK_INTERVAL_MS = 100


#
# Qt key codes that need an explicit, `keyboard`-package-friendly
# name - QKeySequence's default text isn't always a match (e.g.
# it renders Ctrl as "Ctrl", we want "ctrl" to match what
# features/keycombo_manager.py later feeds to keyboard.send()).
#

_NAME_OVERRIDES = {
    Qt.Key_Control: "ctrl",
    Qt.Key_Shift: "shift",
    Qt.Key_Alt: "alt",
    Qt.Key_AltGr: "alt gr",
    Qt.Key_Meta: "windows",
    Qt.Key_Super_L: "windows",
    Qt.Key_Super_R: "windows",
    Qt.Key_Escape: "esc",
    Qt.Key_Tab: "tab",
    Qt.Key_Backspace: "backspace",
    Qt.Key_Return: "enter",
    Qt.Key_Enter: "enter",
    Qt.Key_Space: "space",
    Qt.Key_Delete: "delete",
    Qt.Key_Insert: "insert",
    Qt.Key_Home: "home",
    Qt.Key_End: "end",
    Qt.Key_PageUp: "page up",
    Qt.Key_PageDown: "page down",
    Qt.Key_Up: "up",
    Qt.Key_Down: "down",
    Qt.Key_Left: "left",
    Qt.Key_Right: "right",
    Qt.Key_CapsLock: "caps lock",
    Qt.Key_Print: "print screen",
}

for _i in range(1, 25):

    _NAME_OVERRIDES[getattr(Qt, "Key_F%d" % _i)] = "f%d" % _i


def key_event_name(event):

    key = event.key()

    if key in _NAME_OVERRIDES:

        return _NAME_OVERRIDES[key]

    text = event.text()

    if text and text.isprintable() and text.strip():

        return text.lower()

    try:

        name = QKeySequence(key).toString()

        return name.lower() if name else None

    except Exception:

        return None


class ComboCapturePopup(QWidget):


    def __init__(
        self,
        on_finished,
        timeout=DEFAULT_TIMEOUT,
        max_keys=3,
        parent=None
    ):

        super().__init__(parent)

        self.on_finished = on_finished

        self.timeout = timeout

        self.max_keys = max_keys

        self._captured = []

        self._seen = set()

        self._held = set()

        self._start_time = None

        self._finished = False

        #
        # Deliberately NOT WindowDoesNotAcceptFocus /
        # WA_ShowWithoutActivating like onscreenmenu's other
        # overlays - this popup needs REAL keyboard focus to
        # receive key events at all.
        #

        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint
        )

        self.setFocusPolicy(
            Qt.StrongFocus
        )

        self.resize(
            460,
            240
        )

        layout = QVBoxLayout(self)

        self.title_label = QLabel(
            "Hold the key combo you want to enter (1-3 keys)"
        )

        self.title_label.setWordWrap(True)

        self.title_label.setAlignment(
            Qt.AlignCenter
        )

        layout.addWidget(
            self.title_label
        )

        self.countdown_label = QLabel(
            str(int(timeout))
        )

        self.countdown_label.setAlignment(
            Qt.AlignCenter
        )

        self.countdown_label.setStyleSheet(
            "font-size:56px; color:#00ffff; font-weight:bold;"
        )

        layout.addWidget(
            self.countdown_label
        )

        self.keys_label = QLabel("(waiting for keys...)")

        self.keys_label.setAlignment(
            Qt.AlignCenter
        )

        self.keys_label.setStyleSheet(
            "font-size:20px; color:#e0f8ff;"
        )

        layout.addWidget(
            self.keys_label
        )

        self.setStyleSheet(
            """
            QWidget {
                background:#101020;
                color:#00ffff;
                font-size:16px;
            }
            """
        )

        self.timer = QTimer(self)

        self.timer.setInterval(TICK_INTERVAL_MS)

        self.timer.timeout.connect(
            self._tick
        )


    def start(self):

        self._start_time = time.time()

        self.show()

        self.raise_()

        self.activateWindow()

        self.setFocus(
            Qt.OtherFocusReason
        )

        self.grabKeyboard()

        self.timer.start()


    def _tick(self):

        elapsed = time.time() - self._start_time

        remaining = self.timeout - elapsed

        if remaining <= 0:

            self._finish()

            return

        self.countdown_label.setText(
            str(max(1, math.ceil(remaining)))
        )

        if self._held:

            self.keys_label.setText(
                " + ".join(k.upper() for k in self._held)
            )

        else:

            self.keys_label.setText(
                "(waiting for keys...)"
            )


    def keyPressEvent(
        self,
        event
    ):

        if event.isAutoRepeat():

            return

        name = key_event_name(event)

        if name:

            self._held.add(name)

            if (

                name not in self._seen

                and

                len(self._captured) < self.max_keys

            ):

                self._seen.add(name)

                self._captured.append(name)

        if len(self._captured) >= self.max_keys:

            self._finish()

            return

        event.accept()


    def keyReleaseEvent(
        self,
        event
    ):

        if event.isAutoRepeat():

            return

        name = key_event_name(event)

        if name:

            self._held.discard(name)

        event.accept()


    def _finish(self):

        if self._finished:

            return

        self._finished = True

        self.timer.stop()

        try:

            self.releaseKeyboard()

        except Exception:

            pass

        self.hide()

        if self.on_finished:

            self.on_finished(
                list(self._captured)
            )
