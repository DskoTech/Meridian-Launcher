"""
CyberDeck Keyboard Window Manager

Controls:
- Onscreen keyboard visibility
- Keyboard widget lifecycle
- Text input connection
"""




from keyboard.keyboard_widget import KeyboardWidget

from keyboard.text_input_manager import TextInputManager





class KeyboardWindow:


    def __init__(
        self,
        parent=None
    ):

        self.parent = parent
        self.keyboard = KeyboardWidget()


        self.text_manager = TextInputManager()


        self.keyboard.key_pressed.connect(

            self.text_manager.handle_key

        )


        #
        # Start hidden
        #

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
        target
    ):

        """
        Tell the keyboard where text goes.
        """


        self.text_manager.set_target(

            target

        )





    def controller_move(
        self,
        x,
        y
    ):

        """
        Called by controller thread.
        """


        self.keyboard.move_selection(

            x,

            y

        )





    def controller_select(self):


        self.keyboard.activate_selected()
