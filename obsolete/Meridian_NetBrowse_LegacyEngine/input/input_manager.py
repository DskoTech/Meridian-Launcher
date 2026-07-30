"""
CyberDeck Unified Input Manager

Single source of truth for controller A / B / D-pad
handling.

Several systems (virtual keyboard, popup menus,
browser, fake cursor) all care about the same
buttons. Before this existed, each system polled
controller.state independently, so a single button
press could trigger multiple unrelated actions at
once (e.g. A both clicking a virtual key AND
left-clicking the real cursor position).

InputManager owns edge detection for A/B/D-pad and
decides, based on what currently has "focus", which
single system gets the input:

    keyboard visible  -> keyboard navigation/selection
    a popup is open   -> popup navigation/selection
    otherwise         -> browser + real cursor clicks

Continuous, non-conflicting inputs (right stick
scroll/zoom, shoulder-button tab switching, left
stick cursor movement) are NOT handled here — those
stay owned by BrowserController / ControllerCursor
since nothing else competes for them.
"""


from PySide6.QtCore import QObject, QTimer




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

            "l3": False,

            "dpad_up": False,
            "dpad_down": False,
            "dpad_left": False,
            "dpad_right": False

        }


        self.timer = QTimer()

        self.timer.timeout.connect(
            self.update
        )

        self.timer.start(
            16
        )



    #
    # ---- context ----
    #

    def active_popup(self):

        """
        Returns the currently visible popup
        (menu, search window, URL bar, find bar,
        settings, or any dynamically built menu),
        or None.
        """

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


        return "browser"



    #
    # ---- main loop ----
    #

    def update(self):

        if not getattr(

            self.window,

            "app_focused",

            True

        ):

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

        self._handle_l3(
            state
        )

        self.last["a"] = state.a

        self.last["b"] = state.b

        self.last["l3"] = state.l3

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
        # browser mode -> arrow key emulation / scroll
        #

        browser_controller = self.window.browser_controller

        if up:

            browser_controller.scroll_up()

        if down:

            browser_controller.scroll_down()

        if left:

            browser_controller.arrow_left()

        if right:

            browser_controller.arrow_right()



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
        # browser mode -> left click at fake cursor
        # position (the real Windows cursor)
        #

        self.window.cursor.click_left()

        self._hud_feedback(
            "A / LEFT CLICK"
        )



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

                #
                # Search/URL/Find popups own the shared
                # keyboard while open - B closes the
                # whole popup, not just the keyboard.
                #

                self.window.close_popup()

            else:

                self.window.keyboard_window.hide_keyboard()

                self.window.keyboard_window.text_manager.set_target(
                    None
                )

            return


        if current_mode == "menu":

            popup = self.active_popup()

            if popup is not None:

                self.window.close_popup()

            return


        #
        # browser mode -> right click (context menu)
        #

        self.window.cursor.click_right()

        self._hud_feedback(
            "B / RIGHT CLICK"
        )



    def _handle_l3(
        self,
        state
    ):

        """
        Left stick click resets browser zoom.

        Not contextual - nothing else uses L3, so it
        always resets zoom regardless of what's
        currently focused.
        """

        if not (state.l3 and not self.last["l3"]):

            return

        browser = self.window.browser.current_browser()

        if browser:

            browser.reset_zoom()

            self._hud_feedback(
                "L3 / RESET ZOOM"
            )



    def _hud_feedback(
        self,
        text
    ):

        hud = getattr(
            self.window,
            "hud",
            None
        )

        if hud is not None:

            hud.show_feedback(
                text
            )
