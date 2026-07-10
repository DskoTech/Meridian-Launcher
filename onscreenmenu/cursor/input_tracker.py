"""
onscreenmenu Global Cursor Synchronizer

Keeps fake cursor exactly on top of Windows cursor.
"""


from PySide6.QtCore import QObject, QTimer
from PySide6.QtGui import QCursor





class InputTracker(QObject):


    def __init__(
        self,
        pointer
    ):

        super().__init__()


        self.pointer = pointer


        self.timer = QTimer()


        self.timer.timeout.connect(

            self.sync_cursor

        )


        self.timer.start(

            8

        )





    def sync_cursor(self):


        pos = QCursor.pos()


        self.pointer.set_position(

            pos.x(),

            pos.y(),

            "system"

        )
