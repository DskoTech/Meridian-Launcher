"""
CyberDeck Main Window

Main application window.

Includes:
- Browser
- Controller polling
- Browser controls
- Unified pointer system
- Fake cursor overlay
- Controller menus / popups
- Unified input arbitration (InputManager)
"""


import os
import subprocess
import urllib.parse

from PySide6.QtWidgets import (
    QMainWindow,
    QApplication
)
from ui.keyboard_window import KeyboardWindow
from PySide6.QtGui import QGuiApplication
from PySide6.QtCore import QTimer, Qt


from config import save_config

from browser.tabs import BrowserTabs
from browser.downloads import DownloadManager
from browser.focus_watcher import FocusWatcher
from browser import bookmarks

from controller.controller_thread import ControllerThread


from cursor import (
    ControllerCursor,
    CursorWidget
)

from cursor.pointer_manager import PointerManager
from cursor.input_tracker import InputTracker


from input.browser_controls import BrowserController
from input.input_manager import InputManager


from menus.menu_base import CyberMenu
from menus.browser_menu import BrowserMenu
from menus.tools_menu import ToolsMenu

from ui.search_window import SearchWindow
from ui.url_bar import UrlBar
from ui.find_bar import FindBar
from ui.settings_dialog import SettingsDialog
from ui.hud_overlay import HUDOverlay
from paths import APP_ROOT


#
# osk.bat is expected to live next to the app - the
# project root when running from source, or the
# .exe's own folder once compiled
#

PROJECT_ROOT = APP_ROOT

OSK_BAT_PATH = os.path.join(
    PROJECT_ROOT,
    "osk.bat"
)




class MainWindow(QMainWindow):


    def __init__(
        self,
        config
    ):

        super().__init__()


        self.config = config

        #
        # Window setup
        #

        self.setWindowTitle(

            "CyberDeckBrowser"

        )


        #
        # Tracks whether this app currently has OS
        # focus. When it doesn't, the real-mouse
        # cursor movement/clicks and the HUD overlay
        # are disabled so the controller can't
        # "project" onto other programs.
        #

        self.app_focused = True

        QApplication.instance().applicationStateChanged.connect(
            self.handle_app_state_changed
        )


        #
        # Controller thread
        #

        self.controller = ControllerThread()

        #
        # Select launches osk.bat instead of the
        # built-in virtual keyboard overlay
        #

        self.controller.select_pressed.connect(
            self.run_osk
        )


        #
        # Start gamepad polling on its own thread
        #

        self.controller.start()


        #
        # Browser
        #

        self.browser = BrowserTabs(

            config["homepage"]

        )

        self.browser.close_requested.connect(
            self.close
        )


        self.setCentralWidget(

            self.browser

        )


        #
        # Download manager (needs a WebEngine profile,
        # which now exists since BrowserTabs created
        # its first BrowserView above)
        #

        self.download_manager = DownloadManager()


        #
        # Browser controller mapping (continuous
        # analog behaviors: stick scroll/zoom,
        # shoulder-button tab switching)
        #

        self.browser_controller = BrowserController(

            self.controller,

            self.browser

        )


        #
        # Controller cursor (left stick moves the
        # real Windows cursor directly)
        #

        self.cursor = ControllerCursor(

            self.controller,

            self.config

        )


        #
        # Unified pointer system - tracks the real
        # cursor position so the fake overlay below
        # can follow it
        #

        self.pointer = PointerManager()

        self.input_tracker = InputTracker(

            self.pointer

        )

        QApplication.instance().installEventFilter(

            self.input_tracker

        )


        #
        # Cyberpunk HUD overlay - purely decorative,
        # click-through, sits below the fake cursor
        #

        self.hud = HUDOverlay(
            self.config
        )

        self.hud.show()


        #
        # Fake cursor overlay
        #

        self.cursor_widget = CursorWidget()


        screen = QGuiApplication.primaryScreen()

        screen.geometryChanged.connect(
            self.cursor_widget.update_screen_geometry
        )

        screen.geometryChanged.connect(
            self.hud.update_screen_geometry
        )


        self.cursor_widget.show()

        self.cursor_widget.raise_()

        self.activateWindow()


        self.pointer.position_changed.connect(

            self.update_fake_cursor

        )


        #
        # Cursor update timer
        #

        self.cursor_timer = QTimer()

        self.cursor_timer.timeout.connect(

            self._update_cursor_if_focused

        )

        self.cursor_timer.start(

            16

        )


        #
        # Virtual keyboard system
        #

        self.keyboard_window = KeyboardWindow(
            self
        )


        #
        # Watches the loaded page for a focused text
        # field (e.g. a Google search box) and
        # automatically opens the shared keyboard,
        # typing directly into the page.
        #

        self.focus_watcher = FocusWatcher(

            self,

            self.browser

        )


        #
        # Popup tracking - only one popup (menu,
        # search window, URL bar, find bar,
        # settings, or a dynamically built menu)
        # is ever open at a time.
        #

        self.current_popup = None


        #
        # Menus (Y / X)
        #

        self.browser_menu = BrowserMenu(
            self.handle_browser_menu_select
        )

        self.tools_menu = ToolsMenu(
            self.handle_tools_menu_select
        )

        self.browser_menu.hide()

        self.tools_menu.hide()


        #
        # Search window (Start), URL bar (Enter URL),
        # Find bar (Find In Page), Settings
        #

        self.search_window = SearchWindow(
            config.get(
                "search_engine",
                "https://www.google.com/search?q="
            )
        )

        self.url_bar = UrlBar()

        self.find_bar = FindBar()

        self.settings_dialog = SettingsDialog(
            self.config
        )


        for popup in (

            self.search_window,

            self.url_bar,

            self.find_bar

        ):

            popup.attach_keyboard(
                self.keyboard_window
            )

            popup.hide()


        self.settings_dialog.hide()


        self.search_window.submitted.connect(
            self.handle_search_submit
        )

        self.url_bar.submitted.connect(
            self.handle_url_submit
        )

        self.find_bar.submitted.connect(
            self.handle_find_submit
        )

        self.find_bar.line_edit.textChanged.connect(
            self.handle_find_live
        )

        self.settings_dialog.settings_changed.connect(
            self.handle_settings_changed
        )

        self.settings_dialog.visual_settings_changed.connect(
            self.handle_visual_settings_changed
        )


        #
        # Unified input arbitration
        #
        # Owns A / B / D-pad edge detection and routes
        # them to whichever of {keyboard, popup, browser}
        # currently has focus, so the same press never
        # triggers two unrelated actions.
        #

        self.input_manager = InputManager(

            self.controller,

            self

        )


        #
        # Y / X / Start button popup toggles
        #

        self.last_x = False

        self.last_y = False

        self.last_start = False


        self.menu_timer = QTimer()

        self.menu_timer.timeout.connect(

            self.update_popup_toggles

        )

        self.menu_timer.start(

            50

        )


        #
        # Fullscreen
        #

        if config.get(

            "fullscreen",

            True

        ):

            self.showFullScreen()

        else:

            self.resize(

                1280,

                720

            )



    #
    # ---- popup helpers ----
    #

    def show_popup(
        self,
        popup,
        initial_text=None
    ):

        if (

            self.current_popup is not None

            and

            self.current_popup is not popup

        ):

            self.close_popup()


        self.current_popup = popup

        if hasattr(popup, "open_with_keyboard"):

            popup.open_with_keyboard(
                initial_text or ""
            )

        else:

            popup.show()

            popup.move(
                40,
                100
            )



    def close_popup(self):

        if self.current_popup is None:

            return

        popup = self.current_popup

        if hasattr(popup, "close_popup"):

            popup.close_popup()

        else:

            popup.hide()

        self.current_popup = None



    def toggle_popup(
        self,
        popup,
        initial_text=None
    ):

        if (

            self.current_popup is popup

            and

            popup.isVisible()

        ):

            self.close_popup()

        else:

            self.show_popup(
                popup,
                initial_text
            )



    #
    # ---- fake cursor ----
    #

    def update_fake_cursor(
        self,
        x,
        y
    ):

        """
        Move visual fake cursor.

        Coordinates are screen coordinates.
        """

        self.cursor_widget.update_position(

            int(x),

            int(y)

        )



    #
    # ---- window focus (real cursor + HUD only
    # active while this app has OS focus) ----
    #

    def handle_app_state_changed(
        self,
        state
    ):

        self.app_focused = (

            state == Qt.ApplicationActive

        )

        if hasattr(self, "hud"):

            self.hud.setVisible(
                self.app_focused
            )

        if hasattr(self, "cursor_widget"):

            self.cursor_widget.setVisible(
                self.app_focused
            )



    def _update_cursor_if_focused(self):

        if self.app_focused:

            self.cursor.update()



    #
    # ---- keyboard shortcuts (Select button) ----
    #

    def run_osk(self):

        """
        Launches osk.bat from the project root
        instead of toggling the built-in virtual
        keyboard overlay.
        """

        self.hud.trigger_glitch()

        self.hud.show_feedback(
            "SELECT / OSK"
        )

        try:

            subprocess.Popen(

                OSK_BAT_PATH,

                cwd=PROJECT_ROOT,

                shell=True

            )

        except Exception:

            self.hud.show_feedback(
                "OSK LAUNCH FAILED"
            )



    def toggle_keyboard(self):

        self.keyboard_window.toggle_keyboard()

        self.hud.trigger_glitch()

        self.hud.show_feedback(
            "SELECT / KEYBOARD"
        )



    def show_keyboard(self):

        self.keyboard_window.show_keyboard()



    def hide_keyboard(self):

        self.keyboard_window.hide_keyboard()



    #
    # ---- Y / X / Start popup toggles ----
    #

    def update_popup_toggles(self):

        state = self.controller.state


        if state.y and not self.last_y:

            self.toggle_popup(
                self.browser_menu
            )

            self.hud.trigger_glitch()

            self.hud.show_feedback(
                "Y / MENU"
            )


        if state.x and not self.last_x:

            self.toggle_popup(
                self.tools_menu
            )

            self.hud.trigger_glitch()

            self.hud.show_feedback(
                "X / MENU"
            )


        if state.start and not self.last_start:

            self.toggle_popup(
                self.search_window
            )

            self.hud.trigger_glitch()

            self.hud.show_feedback(
                "START / SEARCH"
            )


        self.last_y = state.y

        self.last_x = state.x

        self.last_start = state.start


        #
        # Keep the HUD's status readouts current
        #

        self.hud.set_controller_connected(
            state.connected
        )

        self.hud.set_mode(

            "CONTROLLER"

            if state.connected

            else "MOUSE + KEYBOARD"

        )



    #
    # ---- Tools (X) menu actions ----
    #

    def handle_tools_menu_select(
        self,
        item
    ):

        self.close_popup()

        browser = self.browser.current_browser()


        if item == "Refresh":

            if browser:

                browser.refresh_page()

        elif item == "Enter URL":

            self.open_url_bar()

        elif item == "Previous Page":

            if browser:

                browser.go_back()

        elif item == "Next Page":

            if browser:

                browser.go_forward()

        elif item == "New Tab":

            self.browser.new_tab()

        elif item == "Close Tab":

            self.browser.close_tab(
                self.browser.currentIndex()
            )

        elif item == "Close Browser":

            self.close()



    def open_url_bar(self):

        browser = self.browser.current_browser()

        current_url = (

            browser.url().toString()

            if browser

            else ""

        )

        self.show_popup(

            self.url_bar,

            initial_text=current_url

        )



    def handle_url_submit(
        self,
        text
    ):

        text = text.strip()

        browser = self.browser.current_browser()

        if text and browser:

            browser.navigate(text)

        self.close_popup()



    #
    # ---- Start button search ----
    #

    def handle_search_submit(
        self,
        text
    ):

        url = self.search_window.build_url(text)

        browser = self.browser.current_browser()

        if url and browser:

            browser.navigate(url)

        self.close_popup()



    #
    # ---- Browser (Y) menu actions ----
    #

    def handle_browser_menu_select(
        self,
        item
    ):

        self.close_popup()


        if item == "History":

            self.show_history()

        elif item == "Downloads":

            self.show_downloads()

        elif item == "Bookmarks":

            self.show_bookmarks()

        elif item == "Translate":

            self.translate_page()

        elif item == "Settings":

            self.open_settings()

        elif item == "Find In Page":

            self.open_find_bar()



    def show_history(self):

        browser = self.browser.current_browser()

        if not browser:

            return


        history = browser.history()

        history_items = history.items()


        labels = [

            (item.title() or item.url().toString())

            for item in history_items

        ]

        if not labels:

            labels = ["No History"]


        def on_select(
            text,
            history=history,
            history_items=history_items,
            labels=labels
        ):

            if text in labels:

                index = labels.index(text)

                try:

                    history.goToItem(
                        history_items[index]
                    )

                except Exception:

                    pass

            self.close_popup()


        menu = CyberMenu(

            "History",

            labels,

            on_select=on_select

        )

        self.show_popup(menu)



    def show_downloads(self):

        names = self.download_manager.list_names()


        def on_select(text):

            self.download_manager.open_containing_folder(
                text
            )

            self.close_popup()


        menu = CyberMenu(

            "Downloads",

            names,

            on_select=on_select

        )

        self.show_popup(menu)



    def show_bookmarks(self):

        browser = self.browser.current_browser()

        saved = bookmarks.load_bookmarks()

        labels = ["+ Add Current Page"] + [

            entry["title"]

            for entry in saved

        ]


        def on_select(

            text,

            saved=saved,

            browser=browser

        ):

            if text == "+ Add Current Page":

                if browser:

                    bookmarks.add_bookmark(

                        browser.title(),

                        browser.url().toString()

                    )

            else:

                for entry in saved:

                    if entry["title"] == text:

                        if browser:

                            browser.navigate(
                                entry["url"]
                            )

                        break

            self.close_popup()


        menu = CyberMenu(

            "Bookmarks",

            labels,

            on_select=on_select

        )

        self.show_popup(menu)



    def translate_page(self):

        browser = self.browser.current_browser()

        if not browser:

            return


        current_url = browser.url().toString()

        translate_url = (

            "https://translate.google.com/translate?sl=auto&tl=en&u="

            +

            urllib.parse.quote(
                current_url,
                safe=""
            )

        )

        browser.navigate(
            translate_url
        )



    def open_settings(self):

        self.show_popup(
            self.settings_dialog
        )



    def handle_settings_changed(
        self,
        sensitivity,
        trigger_boost,
        deadzone
    ):

        self.cursor.apply_settings(

            sensitivity,

            trigger_boost,

            deadzone

        )

        save_config(
            self.config
        )



    def handle_visual_settings_changed(
        self,
        visual_settings
    ):

        self.hud.apply_settings(
            **visual_settings
        )

        save_config(
            self.config
        )



    def open_find_bar(self):

        self.show_popup(
            self.find_bar
        )



    def handle_find_submit(
        self,
        text
    ):

        browser = self.browser.current_browser()

        if browser and text:

            browser.page().findText(
                text
            )



    def handle_find_live(
        self,
        text
    ):

        browser = self.browser.current_browser()

        if browser:

            browser.page().findText(
                text
            )



    #
    # ---- window events ----
    #

    def resizeEvent(
        self,
        event
    ):

        """
        Keep the HUD and cursor overlays covering
        the full screen.
        """

        if hasattr(

            self,

            "hud"

        ):

            self.hud.update_screen_geometry()


        if hasattr(

            self,

            "cursor_widget"

        ):

            self.cursor_widget.update_screen_geometry()


        event.accept()



    def closeEvent(
        self,
        event
    ):

        """
        Shutdown cleanly.
        """

        if hasattr(

            self,

            "controller"

        ):

            self.controller.stop()


        event.accept()
