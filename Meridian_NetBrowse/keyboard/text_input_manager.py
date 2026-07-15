"""
CyberDeck Text Input Manager

Controls text entry for:
- Onscreen keyboard
- Physical keyboard passthrough
- Browser text fields

The onscreen keyboard state and physical keyboard
state are intentionally separate.
"""


from PySide6.QtCore import QObject, Signal

import subprocess
import platform





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





    def set_target(
        self,
        target
    ):

        """
        Sets the current input destination.

        This can later be:
        - QLineEdit
        - browser JavaScript bridge
        - URL bar
        - search field
        """

        self.target = target





    def insert_text(
        self,
        text
    ):


        if self.shift:

            text = text.upper()


            self.shift = False



        self.current_text += text



        self.send_to_target()



    def backspace(self):


        if len(self.current_text) > 0:


            self.current_text = (

                self.current_text[:-1]

            )



        self.send_to_target()





    def enter(self):


        if self.target:


            try:

                self.target.returnPressed.emit()

            except:


                pass





    def toggle_shift(self):

        self.shift = not self.shift





    def clear(self):

        self.current_text = ""

        self.send_to_target()





    def send_to_target(self):

        """
        Send text to active input.

        This avoids changing onscreen
        keyboard appearance.
        """


        self.text_changed.emit(

            self.current_text

        )



        if self.target:


            try:


                self.target.setText(

                    self.current_text

                )


            except:


                pass





    def handle_key(
        self,
        key
    ):

        """
        Receives keys from KeyboardWidget.
        """


        key_id = key.get(

            "id"

        )



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



        value = key.get(

            "value"

        )



        if value:


            self.insert_text(

                value

            )





    def activate_voice_input(self):

        """
        Opens Windows voice typing.

        Uses the Windows built-in system
        rather than creating a separate
        speech engine.
        """


        if platform.system() != "Windows":

            return



        try:


            subprocess.Popen(

                [

                    "explorer.exe",

                    "ms-settings:speech"

                ]

            )


        except:


            pass
