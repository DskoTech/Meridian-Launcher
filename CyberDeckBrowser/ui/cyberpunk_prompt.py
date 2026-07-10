"""
CyberDeck First-Boot Prompt

Asks once, on first run, whether to enable the
cyberpunk HUD/CRT/scanline/glitch effects.

Navigable by:
- Controller (d-pad/stick left-right, A to confirm)
- Keyboard (Left/Right/Tab, Enter)
- Mouse (click a button)

Spins up its own temporary ControllerThread since
the main application's input system doesn't exist
yet at this point in startup.
"""


from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton
)

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QFont

from controller.controller_thread import ControllerThread




class CyberpunkPrompt(QWidget):


    answered = Signal(
        bool
    )



    def __init__(self):

        super().__init__()

        self.setWindowFlags(

            Qt.FramelessWindowHint

        )

        self.setStyleSheet(

            "background-color:#05060c;"

        )


        layout = QVBoxLayout(self)

        layout.setAlignment(
            Qt.AlignCenter
        )


        title = QLabel(
            "ENABLE CYBERPUNK AESTHETICS?"
        )

        title_font = QFont(
            "Consolas"
        )

        title_font.setStyleHint(
            QFont.Monospace
        )

        title_font.setPointSize(
            18
        )

        title_font.setBold(
            True
        )

        title.setFont(
            title_font
        )

        title.setStyleSheet(
            "color:#00ffff;"
        )

        title.setAlignment(
            Qt.AlignCenter
        )

        layout.addWidget(
            title
        )


        subtitle = QLabel(
            "(You can undo this in settings)"
        )

        subtitle_font = QFont(
            "Consolas"
        )

        subtitle_font.setStyleHint(
            QFont.Monospace
        )

        subtitle_font.setPointSize(
            10
        )

        subtitle.setFont(
            subtitle_font
        )

        subtitle.setStyleSheet(

            "color:#b000ff; margin-top:6px; margin-bottom:26px;"

        )

        subtitle.setAlignment(
            Qt.AlignCenter
        )

        layout.addWidget(
            subtitle
        )


        button_row = QHBoxLayout()

        button_row.setAlignment(
            Qt.AlignCenter
        )


        self.yes_button = QPushButton(
            "YES"
        )

        self.no_button = QPushButton(
            "NO"
        )

        for button in (

            self.yes_button,

            self.no_button

        ):

            button.setFixedSize(
                140,
                50
            )

            button.setCursor(
                Qt.PointingHandCursor
            )

            button_row.addWidget(
                button
            )

        layout.addLayout(
            button_row
        )


        self.yes_button.clicked.connect(
            lambda: self._confirm(True)
        )

        self.no_button.clicked.connect(
            lambda: self._confirm(False)
        )


        self.buttons = [

            self.yes_button,

            self.no_button

        ]

        self.selected_index = 0

        self._refresh_button_styles()


        #
        # Temporary controller for this prompt only
        #

        self.controller = ControllerThread()

        self.controller.start()

        self.last_left = False

        self.last_right = False

        self.last_a = False

        self.poll_timer = QTimer()

        self.poll_timer.timeout.connect(
            self._poll_controller
        )

        self.poll_timer.start(
            50
        )



    def _refresh_button_styles(self):

        for index, button in enumerate(
            self.buttons
        ):

            selected = (
                index == self.selected_index
            )

            button.setStyleSheet(

                """
                QPushButton {
                    background:%s;
                    color:#e0f8ff;
                    font-size:16px;
                    font-weight:bold;
                    border:2px solid #00ffff;
                    border-radius:8px;
                }
                """ % (
                    "#006680" if selected else "#101020"
                )

            )



    def keyPressEvent(
        self,
        event
    ):

        if event.key() in (
            Qt.Key_Left,
            Qt.Key_Tab
        ):

            self.selected_index = (
                self.selected_index - 1
            ) % 2

            self._refresh_button_styles()

        elif event.key() == Qt.Key_Right:

            self.selected_index = (
                self.selected_index + 1
            ) % 2

            self._refresh_button_styles()

        elif event.key() in (
            Qt.Key_Return,
            Qt.Key_Enter,
            Qt.Key_Space
        ):

            self._confirm(
                self.selected_index == 0
            )



    def _poll_controller(self):

        state = self.controller.state

        left = (

            state.dpad_left

            or

            state.left_x < -0.5

        )

        right = (

            state.dpad_right

            or

            state.left_x > 0.5

        )

        if left and not self.last_left:

            self.selected_index = (
                self.selected_index - 1
            ) % 2

            self._refresh_button_styles()

        if right and not self.last_right:

            self.selected_index = (
                self.selected_index + 1
            ) % 2

            self._refresh_button_styles()

        if state.a and not self.last_a:

            self._confirm(
                self.selected_index == 0
            )

        self.last_left = left

        self.last_right = right

        self.last_a = state.a



    def _confirm(
        self,
        enabled
    ):

        self.poll_timer.stop()

        self.controller.stop()

        self.answered.emit(
            enabled
        )

        self.close()
