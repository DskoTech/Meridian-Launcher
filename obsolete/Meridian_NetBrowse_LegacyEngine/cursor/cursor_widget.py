"""
CyberDeck DPI Aware Cursor Overlay

Transparent fullscreen cursor overlay.

Features:
- Controller/mouse fake cursor
- DPI aware
- Multi-monitor aware
- Click-through
- Does not steal focus

Draws a cyan reticle at the tracked cursor position
(fed by InputTracker/PointerManager), which mirrors
wherever the real Windows cursor currently is -
whether it got there via physical mouse movement or
via the controller's left stick.
"""


from ui.click_through import make_click_through


from PySide6.QtWidgets import QWidget

from PySide6.QtGui import (
    QPainter,
    QColor,
    QPen,
    QBrush,
    QGuiApplication
)

from PySide6.QtCore import Qt




class CursorWidget(QWidget):


    def __init__(self):

        super().__init__()

        self.setWindowFlags(

            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool |
            Qt.WindowDoesNotAcceptFocus

        )

        self.setAttribute(
            Qt.WA_TransparentForMouseEvents
        )

        self.setAttribute(
            Qt.WA_TranslucentBackground
        )

        self.setAttribute(
            Qt.WA_NoSystemBackground
        )

        self.setFocusPolicy(
            Qt.NoFocus
        )


        self.x = 0

        self.y = 0

        self.scale = 1.0


        self.update_screen_geometry()

        self.make_click_through()



    def update_screen_geometry(self):

        """
        Cover the complete virtual desktop.
        """

        screen = QGuiApplication.primaryScreen()

        if not screen:

            return

        self.scale = screen.devicePixelRatio()

        self.setGeometry(

            screen.virtualGeometry()

        )



    def make_click_through(self):

        """
        Windows-specific:
        makes the overlay invisible to mouse hit testing.
        """

        make_click_through(self)



    def update_position(
        self,
        x,
        y
    ):

        """
        Receives screen coordinates.
        """

        self.x = x

        self.y = y

        self.update()



    def paintEvent(
        self,
        event
    ):

        painter = QPainter(self)

        painter.setRenderHint(
            QPainter.Antialiasing
        )


        size = 18


        painter.setPen(
            QPen(
                QColor(0, 255, 255),
                2
            )
        )

        painter.setBrush(
            QBrush(
                QColor(0, 255, 255, 60)
            )
        )

        painter.drawEllipse(

            self.x - size / 2,

            self.y - size / 2,

            size,

            size

        )

        painter.drawLine(

            self.x - size,
            self.y,

            self.x + size,
            self.y

        )

        painter.drawLine(

            self.x,
            self.y - size,

            self.x,
            self.y + size

        )
