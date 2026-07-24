"""
CyberDeck Chromium View

Qt WebEngine wrapper.
"""


from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtCore import QUrl

# Popups created by createWindow() below need SOMETHING to hold a Python
# reference to them - nothing else does, so without this list they'd be
# garbage-collected (and the underlying Qt widget destroyed) the instant
# createWindow() returns, closing the popup before it ever showed anything.
_popup_keepalive = []


class BrowserView(QWebEngineView):


    def __init__(
        self,
        homepage
    ):

        super().__init__()


        self.homepage=homepage


        self.load(

            QUrl(homepage)

        )

    def createWindow(self, _window_type):
        """QWebEngineView's default implementation returns None, which
        makes window.open() - what most Google/Facebook/Apple sign-in
        flows use for streaming sites' "sign in with..." buttons - fail
        silently. Looks exactly like "the sign-in button does nothing".
        Spawns a real small popup window for the requested page, matching
        how a real browser's OAuth popup looks anyway (its own small
        window, not a new tab in this one) - Chromium loads the actual
        target URL into whatever's returned here right after this call,
        so the placeholder homepage passed to BrowserView() below is
        never actually shown."""
        popup = BrowserView(self.homepage)
        popup.setWindowTitle("Sign in")
        popup.resize(480, 640)
        popup.show()
        _popup_keepalive.append(popup)

        def _forget():
            try:
                _popup_keepalive.remove(popup)
            except ValueError:
                pass
        popup.destroyed.connect(_forget)
        return popup



    def navigate(
        self,
        url
    ):

        if not url.startswith(
            "http"
        ):

            url = (
                "https://"
                +
                url
            )


        self.load(

            QUrl(url)

        )



    def refresh_page(self):

        self.reload()



    def go_back(self):

        self.back()



    def go_forward(self):

        self.forward()



    def zoom_in(self):

        self.setZoomFactor(

            self.zoomFactor()+0.1

        )



    def zoom_out(self):

        self.setZoomFactor(

            self.zoomFactor()-0.1

        )



    def reset_zoom(self):

        self.setZoomFactor(
            1.0
        )
