"""
onscreenmenu Keyboard Window Manager

Controls the onscreen keyboard overlay.
"""

from PySide6.QtWidgets import QWidget

from PySide6.QtCore import Qt

from keyboard.keyboard_widget import KeyboardWidget

from keyboard.text_input_manager import TextInputManager


class KeyboardWindow(QWidget):


    def __init__(
        self,
        parent=None
    ):

        super().__init__(parent)

        #
        # This manager window is invisible.
        #

        self.setWindowFlags(
            Qt.Tool |
            Qt.WindowDoesNotAcceptFocus
        )

        self.hide()

        #
        # Actual keyboard overlay
        #

        self.keyboard = KeyboardWidget()

        #
        # Text handling
        #

        self.text_manager = TextInputManager()

        self.keyboard.key_pressed.connect(
            self.text_manager.handle_key
        )

        self.visible = False


    def show_keyboard(self):

        if self.visible:

            return

        self.visible = True

        self.keyboard.show_keyboard()


    def hide_keyboard(self):

        if not self.visible:

            return

        self.visible = False

        self.keyboard.hide_keyboard()


    def toggle_keyboard(self):

        if self.visible:

            self.hide_keyboard()

        else:

            self.show_keyboard()


    def set_input_target(
        self,
        target,
        max_length=None
    ):

        self.text_manager.set_target(
            target,
            max_length=max_length
        )


    def controller_move(
        self,
        x,
        y
    ):

        self.keyboard.move_selection(
            x,
            y
        )


    def controller_select(self):

        self.keyboard.activate_selected()
