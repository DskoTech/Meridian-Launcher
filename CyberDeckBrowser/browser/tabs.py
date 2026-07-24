"""
CyberDeck Browser Tabs
"""


from PySide6.QtWidgets import (
    QTabWidget,
    QPushButton
)

from PySide6.QtCore import Qt, Signal

import json
import os

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
        startup_url=None,
        session_path=None,
        default_url=None
    ):

        super().__init__()


        self.homepage=homepage

        # A URL to open in the first tab, ALWAYS overriding any saved
        # session - default-browser invocation, or anything else that's
        # explicitly asking to open ONE SPECIFIC link right now, where
        # silently restoring old tabs instead would be surprising. Not
        # what a plugin's own fixed URL should be - see default_url.
        self.startup_url=startup_url

        # A plugin's own fixed/pinned URL (Telegram, Discord, Tubi,
        # Pluto, etc.) - unlike startup_url, this is only a FALLBACK,
        # used when there's no saved session yet (first-ever open). Once
        # a session exists, it's a fallback that stops being needed at
        # all - being pinned to one site doesn't mean there's nothing
        # worth remembering within it (a chat thread, login state, browse
        # position), so a plugin webapp restores exactly like the
        # Browser section does now instead of always resetting to its
        # base URL on every reopen.
        self.default_url=default_url

        # Where this context's "which tabs were open last time" list lives
        # (see MainWindow's __init__ for how this is computed).
        self.session_path = session_path

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


        # First tab(s): an explicit startup URL always wins (default-
        # browser invocation, "open this specific link" from elsewhere) -
        # otherwise restore whatever tabs were open last time for this
        # context (this now includes plugin webapps - see default_url's
        # docstring above), and only fall back to default_url/homepage if
        # there's no saved session (first-ever launch, or the save/load
        # itself failed).
        restored = [] if self.startup_url else self._load_session()
        if restored:
            for url in restored:
                self.new_tab(url)
        else:
            self.new_tab(self.startup_url or self.default_url or self.homepage)

    def _load_session(self):
        if not self.session_path:
            return []
        try:
            with open(self.session_path, "r", encoding="utf-8") as f:
                urls = json.load(f)
            # Sanity-check rather than trust the file blindly - a
            # corrupted/hand-edited session.json should degrade to "no
            # saved session" (falls back to the homepage), not crash
            # startup or open garbage tabs.
            return [u for u in urls if isinstance(u, str) and u.strip()][:20]
        except Exception:
            return []

    def save_session(self):
        """Called from MainWindow.closeEvent right before the window
        actually closes. Best-effort: a failure here should never block
        shutdown, just means next launch falls back to the homepage."""
        if not self.session_path:
            return
        try:
            urls = []
            for i in range(self.count()):
                view = self.widget(i)
                url = view.url().toString() if view else ""
                if url:
                    urls.append(url)
            os.makedirs(os.path.dirname(self.session_path), exist_ok=True)
            with open(self.session_path, "w", encoding="utf-8") as f:
                json.dump(urls, f)
        except Exception:
            pass

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
