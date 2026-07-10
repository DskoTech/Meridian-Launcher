"""
CyberDeck Focus Watcher

Watches the currently loaded web page for a
focused, text-accepting element (input, textarea,
contenteditable) and automatically shows/hides the
shared onscreen keyboard - so clicking into
something like a Google search box brings the
keyboard up without needing to press Select.

QWebEngineView doesn't expose a Qt signal for DOM
focus changes, so this polls document.activeElement
via JavaScript at a modest interval.
"""


from PySide6.QtCore import QObject, QTimer

from browser.dom_field_target import BrowserFieldTarget




FOCUS_CHECK_SCRIPT = (

    "(function(){"

    "var el = document.activeElement;"

    "if (!el) return {active:false};"

    "var tag = el.tagName;"

    "var editable = el.isContentEditable || tag === 'TEXTAREA';"

    "if (!editable && tag === 'INPUT') {"

    "var t = (el.type || 'text').toLowerCase();"

    "var textTypes = ['text','search','email','url','tel','password','number'];"

    "editable = textTypes.indexOf(t) !== -1;"

    "}"

    "if (!editable) return {active:false};"

    "return {active:true, value: (el.value !== undefined ? el.value : el.innerText) || ''};"

    "})();"

)




class FocusWatcher(QObject):


    def __init__(
        self,
        main_window,
        browser_tabs
    ):

        super().__init__()

        self.window = main_window

        self.browser_tabs = browser_tabs

        self.focused = False

        self.timer = QTimer()

        self.timer.timeout.connect(
            self.poll
        )

        self.timer.start(
            400
        )



    def poll(self):

        #
        # Don't fight with our own popups (search,
        # URL bar, find bar) - they manage the shared
        # keyboard themselves.
        #

        if self.window.current_popup is not None:

            return


        browser = self.browser_tabs.current_browser()

        if not browser:

            return


        browser.page().runJavaScript(

            FOCUS_CHECK_SCRIPT,

            self._handle_result

        )



    def _handle_result(
        self,
        result
    ):

        if not isinstance(result, dict):

            return


        active = bool(
            result.get("active")
        )

        value = result.get("value") or ""


        if self.window.current_popup is not None:

            return


        keyboard = self.window.keyboard_window


        if active and not self.focused:

            self.focused = True

            if not keyboard.visible:

                browser = self.browser_tabs.current_browser()

                target = BrowserFieldTarget(
                    browser
                )

                keyboard.text_manager.current_text = value

                keyboard.text_manager.set_target(
                    target
                )

                keyboard.show_keyboard()


        elif not active and self.focused:

            self.focused = False

            keyboard.hide_keyboard()

            keyboard.text_manager.set_target(
                None
            )
