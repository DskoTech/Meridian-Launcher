"""
Base onscreenmenu Controller Menu

Auto-stretches its box height to fit however many items it
currently holds (Y and X menus grow/shrink as shortcuts / key
combos are added or removed), capped so it never runs off-screen.
"""

from PySide6.QtWidgets import QWidget, QListWidget, QApplication
from PySide6.QtCore import Qt


MENU_WIDTH = 380

ROW_HEIGHT = 42

CHROME_HEIGHT = 40

MIN_HEIGHT = 120

MAX_SCREEN_FRACTION = 0.85


class CyberMenu(QWidget):


    def __init__(
        self,
        title,
        items,
        on_select=None
    ):

        super().__init__()

        self.title = title

        self.on_select = on_select

        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.Tool
        )

        self.list = QListWidget(self)

        self.list.itemClicked.connect(
            self._handle_click
        )

        self.list.itemActivated.connect(
            self._handle_click
        )

        self.setStyleSheet(
            """
            QWidget {
                background:#101020;
                color:#00ffff;
                font-size:18px;
            }

            QListWidget {
                border:2px solid #00ffff;
            }

            QListWidget::item:selected {
                background:#004455;
            }
            """
        )

        self.set_items(items)


    def _max_height(self):

        screen = QApplication.primaryScreen()

        if not screen:

            return 600

        return int(

            screen.availableGeometry().height()

            * MAX_SCREEN_FRACTION

        )


    def _auto_resize(self):

        count = max(1, self.list.count())

        height = min(

            max(

                count * ROW_HEIGHT + CHROME_HEIGHT,

                MIN_HEIGHT

            ),

            self._max_height()

        )

        self.resize(
            MENU_WIDTH,
            height
        )

        self.list.resize(
            self.size()
        )


    def _handle_click(
        self,
        item
    ):

        if self.on_select and item:

            self.on_select(item.text())


    def set_items(
        self,
        items
    ):

        self.list.clear()

        self.list.addItems(items)

        if self.list.count() > 0:

            self.list.setCurrentRow(0)

        self._auto_resize()


    def selected_text(self):

        item = self.list.currentItem()

        if item:

            return item.text()

        return None
