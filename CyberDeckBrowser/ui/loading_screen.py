"""
CyberDeck Loading Screen

Brief startup sequence shown before the main
window appears.
"""


from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QProgressBar
)

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QFont




MESSAGES = [

    "INITIALIZING SYSTEM...",

    "LOADING INPUT DRIVERS...",

    "CALIBRATING CONTROLLER...",

    "NETWORK READY",

    "INPUT SYSTEM READY",

    "WELCOME"

]




class LoadingScreen(QWidget):


    finished = Signal()



    def __init__(self):

        super().__init__()

        self.setWindowFlags(

            Qt.FramelessWindowHint

        )

        self.setStyleSheet(

            "background-color: #05060c;"

        )


        layout = QVBoxLayout(self)

        layout.setAlignment(
            Qt.AlignCenter
        )


        title = QLabel(
            "CYBERDECKBROWSER OS"
        )

        title_font = QFont(
            "Consolas"
        )

        title_font.setStyleHint(
            QFont.Monospace
        )

        title_font.setPointSize(
            28
        )

        title_font.setBold(
            True
        )

        title.setFont(
            title_font
        )

        title.setStyleSheet(
            "color:#00ffff; letter-spacing: 4px;"
        )

        title.setAlignment(
            Qt.AlignCenter
        )

        layout.addWidget(
            title
        )


        self.status_label = QLabel(
            ""
        )

        status_font = QFont(
            "Consolas"
        )

        status_font.setStyleHint(
            QFont.Monospace
        )

        status_font.setPointSize(
            11
        )

        self.status_label.setFont(
            status_font
        )

        self.status_label.setStyleSheet(
            "color:#b000ff; margin-top: 24px;"
        )

        self.status_label.setAlignment(
            Qt.AlignCenter
        )

        layout.addWidget(
            self.status_label
        )


        self.progress_bar = QProgressBar()

        self.progress_bar.setFixedWidth(
            420
        )

        self.progress_bar.setRange(
            0,
            100
        )

        self.progress_bar.setTextVisible(
            False
        )

        self.progress_bar.setStyleSheet(

            """
            QProgressBar {
                background:#101020;
                border:2px solid #00ffff;
                border-radius:4px;
                height:14px;
            }

            QProgressBar::chunk {
                background:#00ffff;
                border-radius:2px;
            }
            """

        )

        layout.addWidget(
            self.progress_bar,
            0,
            Qt.AlignCenter
        )


        self.index = 0

        self.timer = QTimer()

        self.timer.timeout.connect(
            self._advance
        )

        self.timer.start(
            380
        )



    def _advance(self):

        if self.index >= len(MESSAGES):

            self.timer.stop()

            self.finished.emit()

            return


        self.status_label.setText(
            MESSAGES[self.index]
        )

        self.progress_bar.setValue(

            int(

                (self.index + 1)

                /

                len(MESSAGES)

                *

                100

            )

        )

        self.index += 1
