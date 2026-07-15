"""
CyberDeck Browser Controller Controls

Converts controller state into browser commands.

D-pad handling now lives in InputManager, since
the d-pad is contextual (keyboard nav / menu nav /
browser arrow keys depending on what's focused).
This class keeps the browser-only concerns that
never conflict with anything else: right stick
scroll/zoom and shoulder-button tab switching. It
also exposes scroll_up/scroll_down/arrow_left/
arrow_right for InputManager to call when the
d-pad should act on the browser.
"""


from PySide6.QtCore import QTimer





class BrowserController:


    def __init__(
        self,
        controller,
        browser_tabs
    ):


        self.controller = controller

        self.browser_tabs = browser_tabs



        self.last_left_shoulder=False

        self.last_right_shoulder=False



        self.timer = QTimer()

        self.timer.timeout.connect(

            self.update

        )

        self.timer.start(

            16

        )



    def update(self):


        state = self.controller.state

        browser = self.browser_tabs.current_browser()

        if not browser:

            return


        #
        # Right stick vertical -> page scroll
        #

        if abs(state.right_y) > .2:

            browser.page().runJavaScript(

                f"window.scrollBy(0,{int(state.right_y*-500)});"

            )


        #
        # Right stick horizontal -> zoom
        #

        if abs(state.right_x) > .5:

            current = browser.zoomFactor()

            browser.setZoomFactor(

                max(

                    .25,

                    min(

                        3.0,

                        current + state.right_x*.05

                    )

                )

            )


        #
        # Shoulder buttons -> tab switching
        #

        if (

            state.left_shoulder

            and

            not self.last_left_shoulder

        ):

            self.previous_tab()


        if (

            state.right_shoulder

            and

            not self.last_right_shoulder

        ):

            self.next_tab()


        self.last_left_shoulder = state.left_shoulder

        self.last_right_shoulder = state.right_shoulder



    def previous_tab(self):

        index = self.browser_tabs.currentIndex()

        if index > 0:

            self.browser_tabs.setCurrentIndex(

                index-1

            )



    def next_tab(self):

        index = self.browser_tabs.currentIndex()

        if index < self.browser_tabs.count()-1:

            self.browser_tabs.setCurrentIndex(

                index+1

            )



    #
    # Called by InputManager in "browser" mode,
    # i.e. no keyboard/menu currently has the d-pad.
    #

    def scroll_up(self):

        browser = self.browser_tabs.current_browser()

        if browser:

            browser.page().runJavaScript(

                "window.scrollBy(0,-100);"

            )



    def scroll_down(self):

        browser = self.browser_tabs.current_browser()

        if browser:

            browser.page().runJavaScript(

                "window.scrollBy(0,100);"

            )



    def arrow_left(self):

        self._send_arrow_key(
            "ArrowLeft",
            37
        )



    def arrow_right(self):

        self._send_arrow_key(
            "ArrowRight",
            39
        )



    def _send_arrow_key(
        self,
        key_name,
        key_code
    ):

        """
        Dispatches a synthetic keyboard event to the
        page so arrow-key-driven pages (carousels,
        slideshows, games) respond to the d-pad.
        """

        browser = self.browser_tabs.current_browser()

        if not browser:

            return

        script = (

            "document.dispatchEvent(new KeyboardEvent("

            "'keydown', {key:'%s', keyCode:%d, which:%d, bubbles:true}"

            "));"

        ) % (

            key_name,

            key_code,

            key_code

        )

        browser.page().runJavaScript(
            script
        )
