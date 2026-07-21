"""
onscreenmenu Main Window

A transparent, click-through, fullscreen overlay that hosts:

- Controller polling
- Fake cursor (real Windows cursor + visual overlay)
- Onscreen keyboard (used only inside onscreenmenu's own popup
  fields - e.g. naming a shortcut or key combo)
- Y menu  -> shortcuts (Meridian Launcher + up to 11 custom)
- X menu  -> Virtual Keyboard, Close Onscreenmenu, + any pre-configured
  key combos (no in-menu add/remove anymore - see KeyComboManager)
- Select  -> recent apps switcher
- R3 (or Ctrl+H) -> hibernate / resume
- L3+R3   -> confirm-and-quit
- Ctrl+T  -> quit

The window itself has no visible content and is click-through, so
it never blocks interaction with whatever's running underneath it.
It stays in the taskbar like a normal app - nothing about
onscreenmenu is hidden from the person running it.
"""

import ctypes
import os

from PySide6.QtWidgets import (
    QMainWindow,
    QApplication,
    QWidget,
    QFileDialog,
    QMessageBox
)

from PySide6.QtGui import QGuiApplication
from PySide6.QtCore import QTimer, Qt

from config import save_config

from controller.controller_thread import ControllerThread

from cursor import (
    ControllerCursor,
    CursorWidget
)

from cursor.pointer_manager import PointerManager
from cursor.input_tracker import InputTracker

from input.input_manager import InputManager

from menus.menu_base import CyberMenu
from menus.shortcuts_menu import ShortcutsMenu
from menus.keycombo_menu import KeyComboMenu
from menus.recent_apps_menu import RecentAppsMenu

from ui.keyboard_window import KeyboardWindow
from ui.name_entry_popup import NameEntryPopup
from ui.combo_capture_popup import ComboCapturePopup

from features.shortcuts_manager import ShortcutsManager
from features.keycombo_manager import (
    KeyComboManager,
    CLOSE_APP_LABEL
)
from features.recent_apps_tracker import RecentAppsTracker
from features.global_hotkeys import GlobalHotkeys
from features import startup
from features.foreign_focus_watcher import ForeignFocusWatcher


class MainWindow(QMainWindow):


    def __init__(
        self,
        config
    ):

        super().__init__()

        self.config = config

        #
        # ---- transparent, click-through, fullscreen window ----
        #

        self.setWindowTitle("onscreenmenu")

        self.setWindowFlags(
            Qt.FramelessWindowHint
        )

        self.setAttribute(
            Qt.WA_TranslucentBackground
        )

        self.setAttribute(
            Qt.WA_NoSystemBackground
        )

        placeholder = QWidget()

        placeholder.setStyleSheet(
            "background: transparent;"
        )

        self.setCentralWidget(placeholder)

        #
        # ---- controller thread ----
        #

        self.controller = ControllerThread()

        self.controller.start()

        #
        # ---- unified pointer system ----
        #

        self.pointer = PointerManager()

        self.cursor = ControllerCursor(
            self.controller,
            self.config
        )

        self.input_tracker = InputTracker(
            self.pointer
        )

        QApplication.instance().installEventFilter(
            self.input_tracker
        )

        #
        # ---- "OSM is on" indicator overlay ----
        # Used to be a fake cursor that followed the real one via this
        # position_changed signal (InputTracker -> PointerManager); it
        # never quite stayed in sync and duplicated what the real cursor
        # already did (clicks always went to the real cursor's position,
        # not the overlay's). Detached now - it's a fixed corner badge,
        # so there's nothing to feed it position updates for anymore.
        #

        self.cursor_widget = CursorWidget()

        screen = QGuiApplication.primaryScreen()

        screen.geometryChanged.connect(
            self.cursor_widget.update_screen_geometry
        )

        self.cursor_widget.show()

        self.cursor_timer = QTimer()

        self.cursor_timer.timeout.connect(
            self._cursor_tick
        )

        self.cursor_timer.start(16)

        #
        # ---- onscreen keyboard (used only in onscreenmenu's own popups) ----
        #

        self.keyboard_window = KeyboardWindow(self)

        #
        # ---- popup tracking ----
        #

        self.current_popup = None

        #
        # ---- Y / X data managers ----
        #

        self.shortcuts = ShortcutsManager(
            self.config,
            save_config
        )

        self.keycombos = KeyComboManager(
            self.config,
            save_config
        )

        self.shortcuts_menu = ShortcutsMenu(
            self.shortcuts.menu_items(),
            on_select=self.handle_shortcuts_menu_select
        )

        self.keycombo_menu = KeyComboMenu(
            self.keycombos.menu_items(),
            on_select=self.handle_keycombo_menu_select
        )

        self.shortcuts_menu.hide()

        self.keycombo_menu.hide()

        #
        # ---- recent apps (Select button) ----
        #

        self.recent_apps = RecentAppsTracker()

        self.recent_apps_menu = None

        #
        # ---- shared name-entry popup (Add Shortcut / Add Key Combo) ----
        #

        self.name_entry_popup = NameEntryPopup("Name")

        self.name_entry_popup.attach_keyboard(
            self.keyboard_window
        )

        self.name_entry_popup.hide()

        self.name_entry_popup.submitted.connect(
            self._handle_name_submit
        )

        self.pending_name_purpose = None

        self.combo_capture_popup = None

        #
        # ---- unified input arbitration ----
        #

        self.input_manager = InputManager(
            self.controller,
            self
        )

        #
        # ---- button edge state ----
        #

        self.last_x = False

        self.last_y = False

        self.last_select = False

        self.last_start = False

        self.last_hibernate_combo = False


        self.hibernating = False

        self.menu_timer = QTimer()

        self.menu_timer.timeout.connect(
            self.update_button_toggles
        )

        self.menu_timer.start(50)

        #
        # Combo watcher runs independently of everything else so
        # Start+Select and L3+R3 always work, even while
        # hibernating.
        #

        self.hibernate_watch_timer = QTimer()

        self.hibernate_watch_timer.timeout.connect(
            self._watch_combos
        )

        self.hibernate_watch_timer.start(50)

        #
        # ---- universal on-screen keyboard auto-invoke ----
        #
        # See features/foreign_focus_watcher.py's module docstring: the
        # fake cursor above already works against any window with no
        # button press needed; this closes the equivalent gap for the
        # keyboard - a third-party installer or UAC prompt grabbing
        # focus now brings up osk.exe on its own, without anyone having
        # to remember to press X first. 400ms is fast enough that the
        # keyboard shows up within a beat of focus actually changing,
        # without polling GetForegroundWindow/OpenInputDesktop hard
        # enough to matter.
        #

        self.foreign_focus_watcher = ForeignFocusWatcher()

        self.foreign_focus_timer = QTimer()

        self.foreign_focus_timer.timeout.connect(
            self._foreign_focus_tick
        )

        self.foreign_focus_timer.start(400)

        #
        # ---- global hotkeys (Ctrl+H / Ctrl+T) ----
        #

        self.hotkeys = GlobalHotkeys()

        self.hotkeys.hibernate_toggle_requested.connect(
            self.toggle_hibernate
        )

        self.hotkeys.quit_requested.connect(
            self.close
        )

        #
        # ---- borderless fullscreen, click-through ----
        #
        # Already frameless (WindowFlags above), so "fullscreen" here just
        # means resizing/positioning to exactly cover the primary screen —
        # not Qt's showFullScreen() state, which behaves like a genuine
        # fullscreen mode switch on some platforms. This keeps the overlay
        # a plain borderless window instead.
        #

        if config.get("fullscreen", True):

            screen_geo = QApplication.primaryScreen().geometry()
            self.move(screen_geo.x(), screen_geo.y())
            self.resize(screen_geo.width(), screen_geo.height())
            self.show()

        else:

            self.resize(1280, 720)

        #
        # Applied after show(), once a native window handle
        # exists.
        #

        QTimer.singleShot(
            0,
            self._make_click_through
        )


    #
    # ---- click-through (Windows-specific) ----
    #

    def _make_click_through(self):

        try:

            hwnd = int(self.winId())

            GWL_EXSTYLE = -20

            WS_EX_TRANSPARENT = 0x00000020

            WS_EX_NOACTIVATE = 0x08000000

            style = ctypes.windll.user32.GetWindowLongW(
                hwnd,
                GWL_EXSTYLE
            )

            ctypes.windll.user32.SetWindowLongW(
                hwnd,
                GWL_EXSTYLE,
                style | WS_EX_TRANSPARENT | WS_EX_NOACTIVATE
            )

        except Exception:

            pass


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

            popup.open_with_keyboard(initial_text or "")

        else:

            popup.show()

            popup.move(40, 100)


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

            self.show_popup(popup, initial_text)


    def show_message(
        self,
        text
    ):

        box = QMessageBox()

        box.setWindowTitle("onscreenmenu")

        box.setText(text)

        box.exec()


    #
    # ---- fake cursor / scroll tick ----
    #

    def _cursor_tick(self):

        if self.hibernating:

            return

        self.cursor.update()

        self.cursor.update_scroll()


    def _foreign_focus_tick(self):

        if self.hibernating:

            return

        self.foreign_focus_watcher.tick()


    def update_fake_cursor(
        self,
        x,
        y
    ):

        self.cursor_widget.update_position(
            int(x),
            int(y)
        )


    #
    # ---- hibernate (R3) ----
    #

    def _watch_combos(self):

        state = self.controller.state

        # Start+Select used to toggle hibernate; that's now unbound (does
        # nothing) and R3 alone does it instead. L3+R3 used to quit (with
        # a confirmation prompt) - removed, for consistency with Meridian
        # Launcher's own L3+R3 removal: a controller-only user with no
        # other way out was one accidental double-click of the sticks
        # away from losing the app, and the confirm prompt itself was
        # awkward to dismiss without a mouse/keyboard. Ctrl+T and the X
        # menu's "Close Onscreenmenu" are still there, and never had a
        # confirmation prompt of their own.
        hibernate_now = state.r3

        if hibernate_now and not self.last_hibernate_combo:

            self.toggle_hibernate()

        self.last_hibernate_combo = hibernate_now


    def toggle_hibernate(self):

        self.hibernating = not self.hibernating

        if self.hibernating:

            self.close_popup()

            self.keyboard_window.hide_keyboard()

            self.cursor_widget.hide()

        else:

            self.cursor_widget.show()


    #
    # ---- Y / X / Select button toggles ----
    #

    def update_button_toggles(self):

        if self.hibernating:

            return

        state = self.controller.state

        if state.y and not self.last_y:

            self.toggle_popup(self.shortcuts_menu)

        if state.x and not self.last_x:

            self.toggle_popup(self.keycombo_menu)

        if state.select and not self.last_select:

            self.open_recent_apps_menu()

        # Start does nothing here - Controls (previously here) moved to
        # the Y menu instead, alongside "Meridian Launcher".

        self.last_y = state.y

        self.last_x = state.x

        self.last_select = state.select

        self.last_start = state.start


    def show_controls_reference(self):

        # Reuses the exact same text shown on first run (features.startup.
        # FIRST_RUN_TEXT) rather than keeping a second, separately-
        # maintained copy of the control list - Start just gives a way to
        # bring it back up on demand instead of only ever seeing it once.

        box = QMessageBox()

        box.setWindowTitle("onscreenmenu - Controls")

        box.setText(startup.FIRST_RUN_TEXT)

        box.setStandardButtons(
            QMessageBox.Ok
        )

        box.exec()


    def _run_osk_bat(self):

        #
        # "Local folder" = wherever onscreenmenu itself is
        # running from (the built exe's folder, or the script's
        # folder when run from source) - not the current working
        # directory, which can vary depending on how it was
        # launched.
        #

        base_dir = os.path.dirname(
            startup.current_exe_path()
        )

        bat_path = os.path.join(
            base_dir,
            "osk.bat"
        )

        if not os.path.isfile(bat_path):

            self.show_message(
                "osk.bat wasn't found in:\n" + base_dir
            )

            return

        try:

            os.startfile(bat_path)

        except Exception as error:

            self.show_message(
                "Couldn't run osk.bat: " + str(error)
            )


    #
    # ---- Shortcuts (Y) menu ----
    #

    def handle_shortcuts_menu_select(
        self,
        item
    ):

        self.close_popup()

        if item == "Add Shortcut":

            self.start_add_shortcut()

        elif item == "Remove Shortcut":

            self.start_remove_shortcut()

        elif item == "Controls":

            self.show_controls_reference()

        else:

            self.shortcuts.run(
                item,
                error_cb=self.show_message
            )


    def start_add_shortcut(self):

        if not self.shortcuts.can_add():

            self.show_message(
                "You've already got 11 custom shortcuts - "
                "remove one before adding another."
            )

            return

        self.pending_name_purpose = "shortcut"

        self.name_entry_popup.set_title("Shortcut Name")

        self.show_popup(self.name_entry_popup)


    def start_remove_shortcut(self):

        names = [entry["name"] for entry in self.shortcuts.custom]

        if not names:

            self.show_message("No custom shortcuts to remove.")

            return

        menu = CyberMenu(
            "Remove Shortcut",
            names,
            on_select=self._remove_shortcut_selected
        )

        self.show_popup(menu)


    def _remove_shortcut_selected(
        self,
        name
    ):

        self.shortcuts.remove(name)

        self.close_popup()

        self._refresh_shortcuts_menu()


    def _refresh_shortcuts_menu(self):

        self.shortcuts_menu.set_items(
            self.shortcuts.menu_items()
        )


    #
    # ---- Key Combos (X) menu ----
    #

    def handle_keycombo_menu_select(
        self,
        item
    ):

        self.close_popup()

        if item == "Virtual Keyboard":

            self._run_osk_bat()

        elif item == CLOSE_APP_LABEL:

            self.close()

        else:

            self.keycombos.run(item)


    # start_add_combo/start_remove_combo (below) are no longer reachable
    # from the X menu — "Add Key Combo"/"Remove Key Combo" were removed
    # from KeyComboManager.menu_items(). Left in place since they're
    # harmless dead code and combos can still be run if pre-configured in
    # config.json's "key_combos" list; only the in-app add/remove UI flow
    # is gone.
    def start_add_combo(self):

        if not self.keycombos.can_add():

            self.show_message(
                "You've already got 20 key combos - "
                "remove one before adding another."
            )

            return

        self.pending_name_purpose = "combo"

        self.name_entry_popup.set_title("Key Combo Name")

        self.show_popup(self.name_entry_popup)


    def start_remove_combo(self):

        names = [entry["name"] for entry in self.keycombos.combos]

        if not names:

            self.show_message("No key combos to remove.")

            return

        menu = CyberMenu(
            "Remove Key Combo",
            names,
            on_select=self._remove_combo_selected
        )

        self.show_popup(menu)


    def _remove_combo_selected(
        self,
        name
    ):

        self.keycombos.remove(name)

        self.close_popup()

        self._refresh_keycombo_menu()


    def _refresh_keycombo_menu(self):

        self.keycombo_menu.set_items(
            self.keycombos.menu_items()
        )


    def _begin_combo_capture(
        self,
        name
    ):

        self.combo_capture_popup = ComboCapturePopup(
            on_finished=self._finish_add_combo
        )

        self.combo_capture_popup.start()


    def _finish_add_combo(
        self,
        keys
    ):

        name = self.pending_name_purpose_value

        self.combo_capture_popup = None

        if not keys:

            self.show_message(
                "No keys captured - combo not saved."
            )

            return

        if not self.keycombos.can_add():

            self.show_message(
                "You've already got 20 key combos - "
                "remove one before adding another."
            )

            return

        if not self.keycombos.add(name, keys):

            self.show_message(
                '"' + name + '" is a reserved name - '
                "please choose a different name for this combo."
            )

            return

        self._refresh_keycombo_menu()


    #
    # ---- shared name-entry submit (routes to shortcut or combo flow) ----
    #

    def _handle_name_submit(
        self,
        text
    ):

        text = text.strip()

        self.close_popup()

        if not text:

            return

        if self.pending_name_purpose == "shortcut":

            self._finish_add_shortcut(text)

        elif self.pending_name_purpose == "combo":

            self.pending_name_purpose_value = text

            self._begin_combo_capture(text)

        self.pending_name_purpose = None


    def _finish_add_shortcut(
        self,
        name
    ):

        path, _ = QFileDialog.getOpenFileName(
            None,
            "Select a file for this shortcut",
            "",
            "All Files (*.*)"
        )

        if not path:

            return

        self.shortcuts.add(name, path)

        self._refresh_shortcuts_menu()


    #
    # ---- Recent Apps (Select) ----
    #

    def open_recent_apps_menu(self):

        entries = self.recent_apps.recent

        titles = [entry["title"] for entry in entries]

        menu = RecentAppsMenu(
            titles,
            on_select=lambda title, entries=entries: (
                self._recent_app_selected(title, entries)
            )
        )

        self.recent_apps_menu = menu

        self.show_popup(menu)


    def _recent_app_selected(
        self,
        title,
        entries
    ):

        self.close_popup()

        for entry in entries:

            if entry["title"] == title:

                self.recent_apps.focus(entry["hwnd"])

                break

        QTimer.singleShot(
            250,
            self._reassert_overlay
        )


    def _reassert_overlay(self):

        """
        Brings onscreenmenu's own overlay pieces (cursor, any
        open popup) back to the top of the z-order after
        switching focus to another program.
        """

        if not self.hibernating:

            self.cursor_widget.raise_()

        if self.current_popup is not None:

            self.current_popup.raise_()

        if self.keyboard_window.visible:

            self.keyboard_window.keyboard.raise_()


    #
    # ---- window events ----
    #

    def resizeEvent(
        self,
        event
    ):

        if hasattr(self, "cursor_widget"):

            screen = QApplication.primaryScreen()

            self.cursor_widget.setGeometry(
                screen.geometry()
            )

        event.accept()


    def closeEvent(
        self,
        event
    ):

        if hasattr(self, "controller"):

            self.controller.stop()

        if hasattr(self, "hotkeys"):

            self.hotkeys.stop()

        event.accept()

        #
        # quitOnLastWindowClosed is disabled (see main.py) so
        # onscreenmenu's various internal dialogs/popups never
        # trigger an accidental app-wide quit - closing the main
        # window itself is the one thing that should actually end
        # the process, so it does so explicitly here.
        #

        QApplication.instance().quit()
