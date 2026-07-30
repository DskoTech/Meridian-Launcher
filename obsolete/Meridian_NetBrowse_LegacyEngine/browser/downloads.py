"""
CyberDeck Download Manager

Accepts downloads to the user's Downloads folder
and keeps a simple in-memory list for the
Downloads menu.

Written defensively since the QWebEngine download
API has changed names across Qt6 minor versions
(QWebEngineDownloadItem -> QWebEngineDownloadRequest).
"""


import os

from PySide6.QtCore import QObject, Signal
from PySide6.QtWebEngineCore import QWebEngineProfile




def _downloads_directory():

    home = os.path.expanduser("~")

    downloads = os.path.join(
        home,
        "Downloads"
    )

    if os.path.isdir(downloads):

        return downloads


    return home




class DownloadManager(QObject):


    download_added = Signal(str)



    def __init__(self):

        super().__init__()

        self.items = []

        profile = QWebEngineProfile.defaultProfile()

        profile.downloadRequested.connect(
            self._handle_download
        )



    def _handle_download(
        self,
        download
    ):

        try:

            filename = download.downloadFileName()

        except Exception:

            filename = "download"


        directory = _downloads_directory()


        try:

            download.setDownloadDirectory(
                directory
            )

            download.setDownloadFileName(
                filename
            )

        except Exception:

            pass


        try:

            download.accept()

        except Exception:

            pass


        path = os.path.join(
            directory,
            filename
        )

        self.items.append(
            {
                "name": filename,
                "path": path
            }
        )

        self.download_added.emit(
            filename
        )



    def list_names(self):

        if not self.items:

            return ["No Downloads"]


        return [
            item["name"]
            for item in self.items
        ]



    def open_containing_folder(
        self,
        name
    ):

        for item in self.items:

            if item["name"] == name:

                folder = os.path.dirname(
                    item["path"]
                )

                try:

                    os.startfile(
                        folder
                    )

                except Exception:

                    pass

                return
