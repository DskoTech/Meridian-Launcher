"""
onscreenmenu Text Input Manager

The custom onscreen keyboard is only ever used for onscreenmenu's
own popup text fields (e.g. naming a new shortcut or key combo) -
it always types into a bound QLineEdit `target`. There is no
system-wide typing mode.
"""

from PySide6.QtCore import QObject, Signal


class TextInputManager(QObject):


    text_changed = Signal(str)


    def __init__(
        self,
        parent=None
    ):

        super().__init__(parent)

        self.current_text = ""

        self.shift = False

        self.target = None

        self.max_length = None


    def set_target(
        self,
        target,
        max_length=None
    ):

        """
        Sets the current input destination - one of
        onscreenmenu's own QLineEdits, or None to clear the
        binding (key presses are then simply ignored).
        """

        self.target = target

        self.max_length = max_length

        self.current_text = ""


    def insert_text(
        self,
        text
    ):

        if self.target is None:

            return

        if self.shift:

            text = text.upper()

            self.shift = False

        if self.max_length is not None:

            if len(self.current_text) >= self.max_length:

                return

            remaining = self.max_length - len(self.current_text)

            text = text[:remaining]

        self.current_text += text

        self.send_to_target()


    def backspace(self):

        if self.target is None:

            return

        if len(self.current_text) > 0:

            self.current_text = self.current_text[:-1]

        self.send_to_target()


    def enter(self):

        if self.target is None:

            return

        try:

            self.target.returnPressed.emit()

        except Exception:

            pass


    def toggle_shift(self):

        self.shift = not self.shift


    def clear(self):

        self.current_text = ""

        self.send_to_target()


    def send_to_target(self):

        self.text_changed.emit(
            self.current_text
        )

        if self.target:

            try:

                self.target.setText(
                    self.current_text
                )

            except Exception:

                pass


    def handle_key(
        self,
        key
    ):

        """
        Receives keys from KeyboardWidget.
        """

        key_id = key.get("id")

        if key_id == "shift":

            self.toggle_shift()

            return

        if key_id == "backspace":

            self.backspace()

            return

        if key_id == "enter":

            self.enter()

            return

        if key_id == "microphone":

            self.activate_voice_input()

            return

        value = key.get("value")

        if value:

            self.insert_text(value)


    def activate_voice_input(self):

        """
        Opens Windows voice typing.
        """

        import platform
        import subprocess

        if platform.system() != "Windows":

            return

        try:

            subprocess.Popen(
                [
                    "explorer.exe",
                    "ms-settings:speech"
                ]
            )

        except Exception:

            pass
