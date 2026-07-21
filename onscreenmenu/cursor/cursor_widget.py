"""
onscreenmenu DPI Aware Cursor Overlay

Transparent fullscreen overlay hosting a small fixed indicator in the
top-left corner, showing onscreenmenu is running.

Used to be a crosshair that tracked the real Windows cursor position
(via InputTracker/PointerManager), redrawn as the controller/mouse
moved. That never quite kept in sync with the real cursor - visibly
lagging/drifting from it - and duplicated the real cursor's job for no
benefit, since clicks were already always being sent to the real
cursor's position (see ControllerCursor.click_left/click_right), not
to wherever this overlay's crosshair happened to be drawn. Detached
now: it's a static badge, not a second pointer, and the real Windows
cursor is the only thing driving clicks/menus.

Features:
- Fixed corner indicator (not real-cursor-synced)
- DPI aware
- Multi-monitor aware
- Click-through
- Does not steal focus
"""

import ctypes

from PySide6.QtWidgets import QWidget

from PySide6.QtGui import (
    QPainter,
    QColor,
    QPen,
    QBrush,
    QFont,
    QGuiApplication
)

from PySide6.QtCore import Qt


# Local (widget-space) position of the indicator badge - top-left corner,
# clear of window chrome/taskbars most setups might have there.
_INDICATOR_X = 28
_INDICATOR_Y = 28
_INDICATOR_RADIUS = 7


class CursorWidget(QWidget):

    def __init__(self):
        super().__init__()

        self.scale = 1.0

        # Overlay window flags
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool |
            Qt.WindowDoesNotAcceptFocus
        )

        # Qt mouse passthrough
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_NoSystemBackground)

        self.setFocusPolicy(Qt.NoFocus)

        self.update_screen_geometry()

        # Windows mouse passthrough
        self.make_click_through()

    def update_screen_geometry(self):
        """Cover the complete virtual desktop."""
        screen = QGuiApplication.primaryScreen()
        if not screen:
            return
        geometry = screen.virtualGeometry()
        self.scale = screen.devicePixelRatio()
        self.setGeometry(geometry)

    def make_click_through(self):
        """Windows-specific: makes the overlay invisible to mouse hit testing."""
        hwnd = int(self.winId())
        GWL_EXSTYLE = -20
        WS_EX_TRANSPARENT = 0x00000020
        WS_EX_NOACTIVATE = 0x08000000
        style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        ctypes.windll.user32.SetWindowLongW(
            hwnd, GWL_EXSTYLE, style | WS_EX_TRANSPARENT | WS_EX_NOACTIVATE
        )

    def update_position(self, x, y):
        """No longer does anything - kept as a harmless no-op so existing
        callers (PointerManager.position_changed, wired up in
        main_window.py) don't need to be ripped out just because the
        indicator no longer moves. The badge is always drawn at a fixed
        corner position; see paintEvent."""
        return

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Cyberpunk cyan "OSM is on" indicator - a soft outer glow ring
        # plus a solid center dot, always in the same spot regardless of
        # where the real cursor is.
        glow_pen = QPen(QColor(0, 255, 255, 90))
        glow_pen.setWidthF(3.0)
        painter.setPen(glow_pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(
            _INDICATOR_X - _INDICATOR_RADIUS - 4,
            _INDICATOR_Y - _INDICATOR_RADIUS - 4,
            (_INDICATOR_RADIUS + 4) * 2,
            (_INDICATOR_RADIUS + 4) * 2,
        )

        pen = QPen(QColor(0, 255, 255))
        pen.setWidthF(2.0)
        painter.setPen(pen)
        painter.setBrush(QBrush(QColor(0, 255, 255)))
        painter.drawEllipse(
            _INDICATOR_X - _INDICATOR_RADIUS,
            _INDICATOR_Y - _INDICATOR_RADIUS,
            _INDICATOR_RADIUS * 2,
            _INDICATOR_RADIUS * 2,
        )

        painter.setFont(QFont("Segoe UI", 8))
        painter.drawText(_INDICATOR_X + _INDICATOR_RADIUS + 8, _INDICATOR_Y + 4, "OSM")

        painter.end()
