"""
Meridian NetBrowse Loading Screen

Brief, plain startup screen shown before the main window appears -
generic (no cyberpunk styling), since Meridian NetBrowse itself has none.
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
    "Starting...",
    "Loading...",
    "Almost ready...",
]


class LoadingScreen(QWidget):

    finished = Signal()

    def __init__(self):
        super().__init__()

        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setStyleSheet("background-color: #1c1e22;")

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)

        title = QLabel("Meridian NetBrowse")
        title_font = QFont()
        title_font.setPointSize(20)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setStyleSheet("color: #e8e8e8;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        self.status_label = QLabel("")
        status_font = QFont()
        status_font.setPointSize(10)
        self.status_label.setFont(status_font)
        self.status_label.setStyleSheet("color: #9a9a9a; margin-top: 16px;")
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedWidth(320)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet(
            """
            QProgressBar {
                border: 1px solid #3a3d42;
                border-radius: 4px;
                background-color: #26282c;
                margin-top: 20px;
            }
            QProgressBar::chunk {
                background-color: #5b8def;
                border-radius: 3px;
            }
            """
        )
        layout.addWidget(self.progress_bar)

        self._step = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._advance)
        self._timer.start(220)

    def _advance(self):
        if self._step < len(MESSAGES):
            self.status_label.setText(MESSAGES[self._step])
        progress = int(min(100, (self._step + 1) * (100 / len(MESSAGES))))
        self.progress_bar.setValue(progress)
        self._step += 1
        if self._step > len(MESSAGES):
            self._timer.stop()
            self.finished.emit()
