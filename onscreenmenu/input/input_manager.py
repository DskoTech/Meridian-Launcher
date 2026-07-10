"""
onscreenmenu Unified Input Manager

Single source of truth for controller A / B / D-pad handling.

    keyboard visible  -> keyboard navigation/selection
    a popup is open   -> popup navigation/selection
    otherwise         -> real cursor clicks (A/B) + real arrow
                          keystrokes (D-pad), since onscreenmenu
                          is standing in for a physical mouse and
                          keyboard

While the main window is hibernating (Start+Select), this manager
does nothing at all - that's handled entirely by MainWindow's
combo watcher, which keeps running regardless.
"""

from PySide6.QtCore import QObject, QTimer

import keyboard


class InputManager(QObject):


    def __init__(
        self,
        controller,
        main_window
    ):

        super().__init__()

        self.controller = controller

        self.window = main_window

        self.last = {

            "a": False,
            "b": False,

            "dpad_up": False,
            "dpad_down": False,
            "dpad_left": False,
            "dpad_right": False

        }

        self.timer = QTimer()

        self.timer.timeout.connect(
            self.update
        )

        self.timer.start(16)


    #
    # ---- context ----
    #

    def active_popup(self):

        popup = getattr(
            self.window,
            "current_popup",
            None
        )

        if popup is not None and popup.isVisible():

            return popup

        return None


    def mode(self):

        if self.window.keyboard_window.visible:

            return "keyboard"

        if self.active_popup() is not None:

            return "menu"

        return "desktop"


    #
    # ---- main loop ----
    #

    def update(self):

        if getattr(self.window, "hibernating", False):

            return

        state = self.controller.state

        current_mode = self.mode()

        self._handle_dpad(
            state,
            current_mode
        )

        self._handle_a(
            state,
            current_mode
        )

        self._handle_b(
            state,
            current_mode
        )

        self.last["a"] = state.a

        self.last["b"] = state.b

        self.last["dpad_up"] = state.dpad_up

        self.last["dpad_down"] = state.dpad_down

        self.last["dpad_left"] = state.dpad_left

        self.last["dpad_right"] = state.dpad_right


    def _handle_dpad(
        self,
        state,
        current_mode
    ):

        up = state.dpad_up and not self.last["dpad_up"]

        down = state.dpad_down and not self.last["dpad_down"]

        left = state.dpad_left and not self.last["dpad_left"]

        right = state.dpad_right and not self.last["dpad_right"]

        if not (up or down or left or right):

            return

        if current_mode == "keyboard":

            kb = self.window.keyboard_window

            if up:

                kb.controller_move(0, -1)

            if down:

                kb.controller_move(0, 1)

            if left:

                kb.controller_move(-1, 0)

            if right:

                kb.controller_move(1, 0)

            return

        if current_mode == "menu":

            popup = self.active_popup()

            if popup is None or not hasattr(popup, "list"):

                return

            row = popup.list.currentRow()

            if up:

                popup.list.setCurrentRow(
                    max(0, row - 1)
                )

            if down:

                popup.list.setCurrentRow(
                    min(popup.list.count() - 1, row + 1)
                )

            return

        #
        # desktop mode -> real arrow keystrokes, so the d-pad
        # acts as arrow keys for whatever has system focus
        #

        try:

            if up:

                keyboard.send("up")

            if down:

                keyboard.send("down")

            if left:

                keyboard.send("left")

            if right:

                keyboard.send("right")

        except Exception:

            pass


    def _handle_a(
        self,
        state,
        current_mode
    ):

        if not (state.a and not self.last["a"]):

            return

        if current_mode == "keyboard":

            self.window.keyboard_window.controller_select()

            return

        if current_mode == "menu":

            popup = self.active_popup()

            if popup is None:

                return

            if hasattr(popup, "selected_text"):

                item = popup.selected_text()

                if item and popup.on_select:

                    popup.on_select(item)

            return

        #
        # desktop mode -> left click at fake cursor position
        # (the real Windows cursor)
        #

        self.window.cursor.click_left()


    def _handle_b(
        self,
        state,
        current_mode
    ):

        if not (state.b and not self.last["b"]):

            return

        if current_mode == "keyboard":

            popup = self.active_popup()

            if popup is not None and hasattr(popup, "close_popup"):

                self.window.close_popup()

            else:

                self.window.keyboard_window.hide_keyboard()

            return

        if current_mode == "menu":

            popup = self.active_popup()

            if popup is not None:

                self.window.close_popup()

            return

        #
        # desktop mode -> right click
        #

        self.window.cursor.click_right()
