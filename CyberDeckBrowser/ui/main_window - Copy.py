"""
CyberDeck Main Window

Main application window.

Contains:

- Browser
- Controller
- Pointer manager
- Fake cursor
- Virtual keyboard
- Browser menus
"""


from PySide6.QtWidgets import (
    QApplication,
    QMainWindow
)

from PySide6.QtCore import (
    QTimer
)

from PySide6.QtGui import (
    QGuiApplication
)


#
# Browser
#

from browser.tabs import BrowserTabs


#
# Controller
#

from controller.controller_thread import ControllerThread


#
# Cursor system
#

from cursor import (
    ControllerCursor,
    CursorWidget
)

from cursor.pointer_manager import PointerManager
from cursor.input_tracker import InputTracker


#
# Keyboard
#

from ui.keyboard_window import KeyboardWindow


#
# Browser control
#

from input.browser_controls import BrowserController
from input.menu_controller import MenuController


#
# Menus
#

from menus.browser_menu import BrowserMenu
from menus.tools_menu import ToolsMenu





class MainWindow(QMainWindow):


    def __init__(self, config):

        super().__init__()

        self.config = config

        #
        # Window
        #

        self.setWindowTitle(
            "CyberDeck Browser"
        )



        #
        # Browser
        #

        self.browser = BrowserTabs(

            config["homepage"]

        )

        self.setCentralWidget(

            self.browser

        )



        #
        # Controller
        #

        self.controller = ControllerThread()

        self.controller.start()



        #
        # Browser controller
        #

        self.browser_controller = BrowserController(

            self.controller,

            self.browser

        )



        #
        # Pointer system
        #

        self.pointer = PointerManager()



        self.cursor = ControllerCursor(

            self.controller

        )



        self.input_tracker = InputTracker(

            self.pointer

        )



        QApplication.instance().installEventFilter(

            self.input_tracker

        )



        #
        # Cursor overlay
        #

        self.cursor_widget = CursorWidget()



        screen = QGuiApplication.primaryScreen()

        screen.geometryChanged.connect(

            self.cursor_widget.update_screen_geometry

        )



        self.cursor_widget.show()



        self.pointer.position_changed.connect(

            self.update_fake_cursor

        )



        #
        # Cursor timer
        #

        self.cursor_timer = QTimer()

        self.cursor_timer.timeout.connect(

            self.cursor.update

        )

        self.cursor_timer.start(16)



        #
        # Keyboard
        #

        self.keyboard_window = KeyboardWindow(self)

               #
        # Controller → Keyboard
        #

        self.controller.select_pressed.connect(
            self.toggle_keyboard
        )

        self.controller.a_pressed.connect(
            self.keyboard_window.controller_select
        )

        self.controller.dpad_up.connect(
            lambda: self.keyboard_window.controller_move(0, -1)
        )

        self.controller.dpad_down.connect(
            lambda: self.keyboard_window.controller_move(0, 1)
        )

        self.controller.dpad_left.connect(
            lambda: self.keyboard_window.controller_move(-1, 0)
        )

        self.controller.dpad_right.connect(
            lambda: self.keyboard_window.controller_move(1, 0)
        )



        #
        # Browser Menus
        #

        self.browser_menu = BrowserMenu()
        self.browser_menu.hide()

        self.tools_menu = ToolsMenu()
        self.tools_menu.hide()
        #
        # Controller Menu Buttons
        #

        self.controller.x_pressed.connect(
            self.toggle_tools_menu
        )

        self.controller.y_pressed.connect(
            self.toggle_browser_menu
        )


        #
        # Menu Controller
        #

        self.menu_controller = MenuController(

            self.controller,

            self

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





    def toggle_keyboard(self):

        self.keyboard_window.toggle_keyboard()



    def show_keyboard(self):

        self.keyboard_window.show_keyboard()



    def hide_keyboard(self):

        self.keyboard_window.hide_keyboard()



    def update_fake_cursor(
        self,
        x,
        y
    ):

        """
        Move the visual cursor using screen coordinates.
        """

        self.cursor_widget.update_position(

            int(x),

            int(y)

        )





        def toggle_browser_menu(self):
            """
            Toggle the Browser Menu (Y button).
            """

        #
        # Close tools menu if open.
        #

        if self.tools_menu.isVisible():

            self.tools_menu.hide()



        #
        # Toggle browser menu.
        #

        if self.browser_menu.isVisible():

            self.browser_menu.hide()

        else:

            self.browser_menu.move(

                40,

                100

            )

            self.browser_menu.show()

            self.browser_menu.raise_()

            self.browser_menu.activateWindow()



    def toggle_tools_menu(self):
        """
        Toggle the Tools Menu (X button).
        """

        #
        # Close browser menu if open.
        #

        if self.browser_menu.isVisible():

            self.browser_menu.hide()



        #
        # Toggle tools menu.
        #

        if self.tools_menu.isVisible():

            self.tools_menu.hide()

        else:

            self.tools_menu.move(

                40,

                100

            )

            self.tools_menu.show()

            self.tools_menu.raise_()

            self.tools_menu.activateWindow()



    def toggle_keyboard(self):
        """
        Show or hide the virtual keyboard.
        """

        self.keyboard_window.toggle_keyboard()



    def show_keyboard(self):
        """
        Show the virtual keyboard.
        """

        self.keyboard_window.show_keyboard()



    def hide_keyboard(self):
        """
        Hide the virtual keyboard.
        """

        self.keyboard_window.hide_keyboard()



    def update_fake_cursor(
        self,
        x,
        y
    ):
        """
        Update the visual controller cursor.
        """

        self.cursor_widget.update_position(

            int(x),

            int(y)

        )



    def resizeEvent(
        self,
        event
    ):

        """
        Keep cursor overlay fullscreen.
        """


        if hasattr(

            self,

            "cursor_widget"

        ):


            screen = QApplication.primaryScreen()


            self.cursor_widget.setGeometry(

                screen.geometry()

            )



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
    
