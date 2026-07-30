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
        homepage,
        startup_url=None
    ):

        super().__init__()


        self.homepage=homepage

        # A URL to open in the first tab instead of the homepage (default-
        # browser / command-line invocation). Homepage still applies to
        # every tab opened afterward.
        self.startup_url=startup_url


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


        # First tab: the startup URL if we were handed one, else homepage.
        self.new_tab(self.startup_url or self.homepage)



    def new_tab(self, url=None):

        browser=BrowserView(

            url or self.homepage

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
