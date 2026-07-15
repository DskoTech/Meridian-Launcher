"""
CyberDeck Chromium View

Qt WebEngine wrapper.
"""


from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtCore import QUrl



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
