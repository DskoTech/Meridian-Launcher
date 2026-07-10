"""
onscreenmenu DPI Aware Cursor Overlay

Transparent fullscreen cursor overlay.

Features:
- Controller/mouse fake cursor
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
    QGuiApplication
)


from PySide6.QtCore import Qt





class CursorWidget(QWidget):


    def __init__(self):

        super().__init__()



        self.x = 0

        self.y = 0


        self.scale = 1.0



        #
        # Overlay window flags
        #

        self.setWindowFlags(

            Qt.FramelessWindowHint |

            Qt.WindowStaysOnTopHint |

            Qt.Tool |

            Qt.WindowDoesNotAcceptFocus

        )



        #
        # Qt mouse passthrough
        #

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



        self.update_screen_geometry()



        #
        # Windows mouse passthrough
        #

        self.make_click_through()





    def update_screen_geometry(self):

        """
        Cover the complete virtual desktop.
        """


        screen = QGuiApplication.primaryScreen()


        if not screen:

            return



        geometry = screen.virtualGeometry()



        self.scale = screen.devicePixelRatio()



        self.setGeometry(

            geometry

        )





    def make_click_through(self):

        """
        Windows-specific:
        makes the overlay invisible to mouse hit testing.
        """


        hwnd = int(

            self.winId()

        )


        GWL_EXSTYLE = -20


        WS_EX_TRANSPARENT = 0x00000020


        WS_EX_NOACTIVATE = 0x08000000



        style = ctypes.windll.user32.GetWindowLongW(

            hwnd,

            GWL_EXSTYLE

        )


        ctypes.windll.user32.SetWindowLongW(

            hwnd,

            GWL_EXSTYLE,

            style |

            WS_EX_TRANSPARENT |

            WS_EX_NOACTIVATE

        )





    def update_position(
        self,
        x,
        y
    ):

        """
        Receives screen coordinates.

        Converts to overlay-local coordinates.
        """


        screen = QGuiApplication.primaryScreen()


        if not screen:

            return



        geometry = screen.virtualGeometry()



        self.x = (

            x - geometry.x()

        ) / self.scale



        self.y = (

            y - geometry.y()

        ) / self.scale



        self.update()





    def paintEvent(
        self,
        event
    ):


        painter = QPainter(

            self

        )


        painter.setRenderHint(

            QPainter.Antialiasing

        )



        #
        # Cyberpunk cyan cursor
        #

        pen = QPen(

            QColor(

                0,

                255,

                255

            )

        )


        pen.setWidthF(

            2.5

        )


        painter.setPen(

            pen

        )



        #
        # Crosshair
        #

        painter.drawLine(

            self.x - 12,

            self.y,

            self.x + 12,

            self.y

        )


        painter.drawLine(

            self.x,

            self.y - 12,

            self.x,

            self.y + 12

        )



        #
        # Center dot
        #

        painter.setBrush(

            QBrush(

                QColor(

                    0,

                    255,

                    255

                )

            )

        )


        painter.drawEllipse(

            self.x - 3,

            self.y - 3,

            6,

            6

        )


        painter.end()
