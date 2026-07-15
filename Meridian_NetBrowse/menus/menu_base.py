"""
Base CyberDeck Controller Menu
"""


from PySide6.QtWidgets import QWidget, QListWidget
from PySide6.QtCore import Qt



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


        self.resize(
            320,
            420
        )


        self.list = QListWidget(
            self
        )


        self.list.addItems(
            items
        )


        self.list.resize(
            self.size()
        )


        if self.list.count() > 0:

            self.list.setCurrentRow(0)


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



    def _handle_click(
        self,
        item
    ):

        """
        Mouse/touch selection also triggers the action,
        matching controller A-button behavior.
        """

        if self.on_select and item:

            self.on_select(
                item.text()
            )



    def set_items(
        self,
        items
    ):

        """
        Rebuild list contents for reusable dynamic
        menus (history, downloads, bookmarks).
        """

        self.list.clear()

        self.list.addItems(
            items
        )

        if self.list.count() > 0:

            self.list.setCurrentRow(0)



    def selected_text(self):

        item=self.list.currentItem()


        if item:

            return item.text()


        return None
