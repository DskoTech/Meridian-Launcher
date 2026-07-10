"""
CyberDeck Browser Tabs
"""


from PySide6.QtWidgets import (
    QTabWidget,
    QPushButton
)

from PySide6.QtCore import Qt, Signal

from browser.browser_view import BrowserView




class BrowserTabs(QTabWidget):


    #
    # Emitted when the corner close button is
    # clicked - MainWindow closes the app on this.
    #

    close_requested = Signal()



    def __init__(
        self,
        homepage
    ):

        super().__init__()


        self.homepage=homepage


        self.setTabsClosable(
            True
        )


        self.tabCloseRequested.connect(

            self.close_tab

        )


        #
        # Normal close button in the tab bar corner,
        # since fullscreen/frameless windows hide the
        # native OS titlebar close button.
        #

        self.close_program_button = QPushButton(
            "\u2715"
        )

        self.close_program_button.setFixedSize(
            26,
            26
        )

        self.close_program_button.setToolTip(
            "Close CyberDeckBrowser"
        )

        self.close_program_button.setCursor(
            Qt.PointingHandCursor
        )

        self.close_program_button.clicked.connect(

            self.close_requested.emit

        )

        self.setCornerWidget(

            self.close_program_button,

            Qt.TopRightCorner

        )


        self.new_tab()



    def new_tab(self):

        browser=BrowserView(

            self.homepage

        )


        index=self.addTab(

            browser,

            "New Tab"

        )


        self.setCurrentIndex(

            index

        )


    def close_tab(
        self,
        index
    ):

        if self.count()>1:

            self.removeTab(
                index
            )



    def current_browser(self):

        return self.currentWidget()
