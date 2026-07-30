"""
CyberDeck Input Tracker

Polls the real Windows cursor position and feeds it
into PointerManager, so the fake cursor overlay
follows the real cursor regardless of whether it
moved via physical mouse or via the controller's
left stick (which moves the real cursor directly).
"""


from PySide6.QtCore import QObject, QTimer
from PySide6.QtGui import QCursor




class InputTracker(QObject):


    def __init__(
        self,
        pointer_manager,
        interval=8
    ):

        super().__init__()

        self.pointer_manager = pointer_manager

        self.timer = QTimer()

        self.timer.timeout.connect(
            self._poll
        )

        self.timer.start(
            interval
        )



    def _poll(self):

        position = QCursor.pos()

        self.pointer_manager.set_position(

            position.x(),

            position.y()

        )
